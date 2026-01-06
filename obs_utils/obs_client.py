# -*- coding: utf-8 -*-
"""
OBS客户端配置和工具函数
"""
import json
import os
import re
import uuid
import traceback
import asyncio
from io import BytesIO
from datetime import datetime
from typing import Optional
import aiohttp
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
    'endpoint': 'http://obs.cn-east-338.hehcso.com',
    'access_key': 'SNEIPXFWBJMMXE8IH4RL',
    'secret_key': 'P5RN40MY9jyuFV6WlbiGsD0BsSgltwkzTwZrPjxf',
    'bucket_name': 'obs-s03238-0001',
    'secure': False,
    'base_url': 'http://obs-s03238-0001.obs.cn-east-338.hehcso.com',
    'activate': True  # 默认启用OBS
})

print(json.dumps(OBS_CONFIG, indent=4))
# 创建OBS客户端实例
obs_client = ObsClient(
    access_key_id=OBS_CONFIG['access_key'],
    secret_access_key=OBS_CONFIG['secret_key'],
    server=OBS_CONFIG['endpoint'],
    is_secure=OBS_CONFIG['secure']
)


def ensure_bucket_exists():
    """确保存储桶存在，如果不存在则创建"""
    try:
        # 检查桶是否存在
        resp = obs_client.headBucket(OBS_CONFIG['bucket_name'])

        print(f"ensure_bucket_exists headBucket resp: {json.dumps(resp, indent=4)}")
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
            endpoint = OBS_CONFIG['base_url'].rstrip('/')
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

def download_file(object_name: str) -> bytes:
    """
    从OBS下载文件
    
    Args:
        object_name: 对象名称（文件在OBS中的路径）
    
    Returns:
        文件的二进制数据
    """
    try:
        resp = obs_client.getContent(
            OBS_CONFIG['bucket_name'],
            object_name
        )
        
        # 返回码为2xx时，接口调用成功
        if resp.status < 300:
            return resp.body.buffer
        else:
            error_msg = f"下载文件失败: status={resp.status}, errorCode={resp.errorCode}, errorMessage={resp.errorMessage}"
            print(error_msg)
            raise Exception(error_msg)
        
    except Exception as e:
        print(f"从OBS下载文件时出错: {e}")
        print(traceback.format_exc())
        raise


async def download_file_with_aiohttp(url: str) -> bytes:
    """
    使用aiohttp下载文件
    
    Args:
        url: 文件的完整访问URL
    
    Returns:
        文件的二进制数据
    """
    try:
        # 创建不验证SSL证书的连接器（用于处理自签名证书）
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    downloaded_data = await response.read()
                    return downloaded_data
                else:
                    error_msg = f"下载文件失败: HTTP状态码={response.status}"
                    print(error_msg)
                    raise Exception(error_msg)
    except aiohttp.ClientError as e:
        error_msg = f"aiohttp下载文件时出错: {e}"
        print(error_msg)
        print(traceback.format_exc())
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"下载文件时出错: {e}"
        print(error_msg)
        print(traceback.format_exc())
        raise


def extract_object_name_from_url(url: str) -> str:
    """
    从URL中提取对象名称
    
    Args:
        url: 文件的完整访问URL
    
    Returns:
        对象名称
    """
    # URL格式: {base_url}/{bucket_name}/{object_name}
    # 例如: https://obs-s03238-0001.obs.cn-east-338.hehcso.com/obs-s03238-0001/2024-01-01-test-uuid.txt
    base_url = OBS_CONFIG['base_url'].rstrip('/')
    bucket_name = OBS_CONFIG['bucket_name']
    
    # 移除base_url前缀
    if url.startswith(base_url):
        object_name = url[len(base_url) + 1:]  # +1 是为了跳过斜杠
        # 移除bucket_name前缀
        if object_name.startswith(bucket_name + '/'):
            object_name = object_name[len(bucket_name) + 1:]
        return object_name
    else:
        # 如果URL格式不匹配，尝试直接提取最后一个斜杠后的内容
        parts = url.split('/')
        # 找到bucket_name的位置，然后取后面的部分
        try:
            bucket_index = parts.index(bucket_name)
            return '/'.join(parts[bucket_index + 1:])
        except ValueError:
            # 如果找不到bucket_name，返回最后一个部分
            return parts[-1]


def main():
    """测试上传和下载功能"""
    print("=" * 50)
    print("开始测试OBS文件上传和下载功能")
    print("=" * 50)
    
    try:
        # 创建测试文件内容
        test_content = f"这是一个测试文件\n上传时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n测试内容: Hello OBS!"
        file_data = test_content.encode('utf-8')
        file_name = "test_upload.md"
        content_type = "text/plain; charset=utf-8"
        
        print(f"\n准备上传文件: {file_name}")
        print(f"文件大小: {len(file_data)} 字节")
        print(f"内容类型: {content_type}")
        
        # 执行上传
        url = upload_file(file_data, file_name, content_type)
        
        print(f"\n✓ 上传成功！")
        print(f"文件访问URL: {url}")
        
        # 使用aiohttp下载文件
        print(f"\n开始使用aiohttp下载文件...")
        print(f"下载URL: {url}")
        
        # 使用asyncio运行异步下载函数
        downloaded_data = asyncio.run(download_file_with_aiohttp(url))
        
        print(f"✓ aiohttp下载成功！")
        print(f"下载文件大小: {len(downloaded_data)} 字节")
        
        # 验证下载的内容
        downloaded_content = downloaded_data.decode('utf-8')
        print(f"\n下载的文件内容:")
        print("-" * 50)
        print(downloaded_content)
        print("-" * 50)
        
        # 验证内容是否一致
        if downloaded_data == file_data:
            print("\n✓ 验证通过：下载的文件内容与上传的文件内容一致")
        else:
            print("\n✗ 警告：下载的文件内容与上传的文件内容不一致")
        
        print("\n" + "=" * 50)
        print("测试完成")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        print(traceback.format_exc())
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
