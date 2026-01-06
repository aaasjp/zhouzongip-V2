# -*- coding: utf-8 -*-
"""
统一存储客户端，根据配置自动选择使用OBS或MinIO
"""
import json
import os
from typing import Optional

# 加载配置文件
def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()

# 获取OBS和MinIO配置
OBS_CONFIG = CONFIG.get('obs', {})
MINIO_CONFIG = CONFIG.get('minio', {})

# 检查哪个存储服务被激活
OBS_ACTIVATE = OBS_CONFIG.get('activate', True)  # 默认启用OBS
MINIO_ACTIVATE = MINIO_CONFIG.get('activate', False)  # 默认关闭MinIO

# 确定使用的存储服务
if OBS_ACTIVATE:
    STORAGE_TYPE = 'obs'
elif MINIO_ACTIVATE:
    STORAGE_TYPE = 'minio'
else:
    # 如果都没有激活，默认使用OBS
    STORAGE_TYPE = 'obs'
    print("警告: OBS和MinIO都未激活，默认使用OBS")

# 导入对应的存储客户端
if STORAGE_TYPE == 'obs':
    from obs_utils.obs_client import upload_file as obs_upload_file
    _upload_file_impl = obs_upload_file
    print(f"使用OBS存储服务")
else:
    from minio_utils.minio_client import upload_file as minio_upload_file
    _upload_file_impl = minio_upload_file
    print(f"使用MinIO存储服务")


def upload_file(file_data: bytes, file_name: str, content_type: Optional[str] = None, use_public_url: bool = True) -> str:
    """
    统一文件上传接口，根据配置自动选择使用OBS或MinIO
    
    Args:
        file_data: 文件二进制数据
        file_name: 原始文件名
        content_type: 文件MIME类型
        use_public_url: 是否使用公共URL（仅MinIO支持，OBS忽略此参数）
    
    Returns:
        文件的访问URL
    """
    # 如果使用OBS，忽略use_public_url参数
    if STORAGE_TYPE == 'obs':
        return _upload_file_impl(file_data, file_name, content_type)
    else:
        # MinIO支持use_public_url参数
        return _upload_file_impl(file_data, file_name, content_type, use_public_url)

