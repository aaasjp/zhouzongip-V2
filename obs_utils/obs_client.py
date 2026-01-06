# -*- coding: utf-8 -*-
"""
OBS客户端配置和工具函数
"""
import json
import os
import re
import uuid
import traceback
from io import BytesIO
from datetime import datetime
from typing import Optional
from obs import ObsClient, CreateBucketHeader, HeadPermission, PutObjectHeader

# 从config.json读取OBS配置
def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()

# OBS配置（从config.json读取）
OBS_CONFIG = CONFIG.get('obs', {
    'endpoint': 'http://10.250.0.3',
    'access_key': 'SNEIPXFWBJMMXE8IH4RL',
    'secret_key': 'P5RN40MY9jyuFV6WlbiGsD0BsSgltwkzTwZrPjxf',
    'bucket_name': 'gaoguanip-files',
    'activate': True  # 默认启用OBS
})

# 创建OBS客户端实例
obs_client = ObsClient(
    access_key_id=OBS_CONFIG['access_key'],
    secret_access_key=OBS_CONFIG['secret_key'],
    server=OBS_CONFIG['endpoint']
)


def ensure_bucket_exists():
    """确保存储桶存在，如果不存在则创建"""
    try:
        # 检查桶是否存在
        resp = obs_client.headBucket(OBS_CONFIG['bucket_name'])
        
        # 返回码为2xx时，桶存在
        if resp.status < 300:
            print(f"存储桶 '{OBS_CONFIG['bucket_name']}' 已存在")
            return True
        elif resp.status == 404:
            # 桶不存在，创建桶
            print(f"存储桶 '{OBS_CONFIG['bucket_name']}' 不存在，开始创建...")
            
            # 创建桶的附加头域，桶ACL是私有桶，存储类型是标准访问存储
            header = CreateBucketHeader(
                aclControl=HeadPermission.PRIVATE,
                storageClass="STANDARD"
            )
            
            # 从endpoint中提取region（如果endpoint包含region信息）
            # 如果endpoint是 http://10.250.0.3 这样的格式，可能需要指定location
            # 这里先尝试不指定location，如果失败再处理
            location = None  # 某些OBS服务可能不需要location
            
            # 创建桶
            resp = obs_client.createBucket(OBS_CONFIG['bucket_name'], header, location)
            
            if resp.status < 300:
                print(f"存储桶 '{OBS_CONFIG['bucket_name']}' 创建成功")
                return True
            else:
                print(f"创建存储桶失败: status={resp.status}, errorCode={resp.errorCode}, errorMessage={resp.errorMessage}")
                return False
        else:
            print(f"检查存储桶失败: status={resp.status}, errorCode={resp.errorCode}, errorMessage={resp.errorMessage}")
            return False
            
    except Exception as e:
        print(f"操作存储桶时出错: {e}")
        print(traceback.format_exc())
        return False


def upload_file(file_data: bytes, file_name: str, content_type: Optional[str] = None) -> str:
    """
    上传文件到OBS
    
    Args:
        file_data: 文件二进制数据
        file_name: 原始文件名
        content_type: 文件MIME类型
    
    Returns:
        文件的访问URL
    """
    try:
        # 确保存储桶存在
        ensure_bucket_exists()
        
        # 生成唯一文件名（避免文件名冲突）
        file_ext = os.path.splitext(file_name)[1]  # 获取文件扩展名
        file_base_name = os.path.splitext(file_name)[0]  # 获取文件名（不含扩展名）
        
        # 处理文件名：移除或替换特殊字符，限制长度
        # 替换特殊字符为下划线，保留中文字符、字母、数字、连字符和下划线
        safe_file_name = re.sub(r'[^\w\u4e00-\u9fa5-]', '_', file_base_name)
        # 限制文件名长度（避免过长）
        if len(safe_file_name) > 100:
            safe_file_name = safe_file_name[:100]
        
        # 生成唯一标识
        unique_id = str(uuid.uuid4())
        
        # 设置对象路径（可以按日期分类）
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        object_name = f"{date_prefix}-{safe_file_name}-{unique_id}{file_ext}"
        
        # 上传对象的附加头域
        headers = PutObjectHeader()
        # 设置MIME类型
        headers.contentType = content_type or 'application/octet-stream'
        
        # 将 bytes 转换为临时文件或直接上传
        # OBS的putFile方法需要文件路径，putContent方法可以直接上传bytes
        # 这里使用putContent方法
        resp = obs_client.putContent(
            OBS_CONFIG['bucket_name'],
            object_name,
            content=file_data,
            headers=headers
        )
        
        # 返回码为2xx时，接口调用成功
        if resp.status < 300:
            # 构建文件访问URL
            # OBS的URL格式通常是: http://endpoint/bucket_name/object_name
            endpoint = OBS_CONFIG['endpoint'].rstrip('/')
            url = f"{endpoint}/{OBS_CONFIG['bucket_name']}/{object_name}"
            return url
        else:
            error_msg = f"上传文件失败: status={resp.status}, errorCode={resp.errorCode}, errorMessage={resp.errorMessage}"
            print(error_msg)
            raise Exception(error_msg)
        
    except Exception as e:
        print(f"上传文件到OBS时出错: {e}")
        print(traceback.format_exc())
        raise


def get_file_url(object_name: str, expires_seconds: int = 604800) -> str:
    """
    获取文件的预签名URL
    
    Args:
        object_name: OBS中的对象名称（路径）
        expires_seconds: URL有效期（秒），默认7天
    
    Returns:
        文件的预签名URL
    """
    try:
        resp = obs_client.createSignedUrl(
            method='GET',
            bucketName=OBS_CONFIG['bucket_name'],
            objectKey=object_name,
            expires=expires_seconds
        )
        
        if resp.status < 300:
            return resp.body.signedUrl
        else:
            error_msg = f"获取文件URL失败: status={resp.status}, errorCode={resp.errorCode}, errorMessage={resp.errorMessage}"
            print(error_msg)
            raise Exception(error_msg)
    except Exception as e:
        print(f"获取文件URL时出错: {e}")
        print(traceback.format_exc())
        raise


def delete_file(object_name: str) -> bool:
    """
    删除OBS中的文件
    
    Args:
        object_name: OBS中的对象名称（路径）
    
    Returns:
        是否删除成功
    """
    try:
        resp = obs_client.deleteObject(OBS_CONFIG['bucket_name'], object_name)
        
        if resp.status < 300:
            return True
        else:
            print(f"删除文件失败: status={resp.status}, errorCode={resp.errorCode}, errorMessage={resp.errorMessage}")
            return False
    except Exception as e:
        print(f"删除文件时出错: {e}")
        print(traceback.format_exc())
        return False

