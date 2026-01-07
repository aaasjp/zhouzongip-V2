from obs import ObsClient
from obs import PutObjectHeader
import os
import traceback
import asyncio
import aiohttp

# 推荐通过环境变量获取AKSK，这里也可以使用其他外部引入方式传入，如果使用硬编码可能会存在泄露风险
# 您可以登录访问管理控制台获取访问密钥AK/SK，获取方式请参见https://support.huaweicloud.com/usermanual-ca/ca_01_0003.html。
# 运行本代码示例之前，请确保已设置环境变量AccessKeyID和SecretAccessKey
ak = "SNEIPXFWBJMMXE8IH4RL"
sk = "P5RN40MY9jyuFV6WlbiGsD0BsSgltwkzTwZrPjxf"
# 【可选】如果使用临时AKSK和SecurityToken访问OBS，则同样推荐通过环境变量获取
# security_token = os.getenv("SecurityToken")#  server填写Bucket对应的Endpoint, 这里以华北-北京四为例，其他地区请按实际情况填写
server = "https://obs.cn-east-338.hehcso.com"
# 创建obsClient实例
# 如果使用临时AKSK和SecurityToken访问OBS，需要在创建实例时通过security_token参数指定securityToken值
obsClient = ObsClient(access_key_id=ak, secret_access_key=sk, server=server,ssl_verify=False)
# 上传文件
file_url = None
try:
    # 上传对象的附加头域
    headers = PutObjectHeader()
    # 【可选】待上传对象的MIME类型
    headers.contentType = 'text/plain'
    # 【可选】设置对象的ACL权限，可选值：private（私有）、public-read（公共读）、public-read-write（公共读写）、bucket-owner-full-control（桶拥有者完全控制）
    headers.acl = 'public-read'  # 可以根据需要修改为 public-read、public-read-write 等
    
    bucketName = "obs-s03238-0001"
    # 对象名，即上传后的文件名
    objectKey = "OCR接口说明文档.md"
    # 待上传文件的完整路径，如aa/bb.txt
    file_path = 'docs/OCR接口说明文档.md'
    # 上传文件的自定义元数据
    metadata = {'meta1': 'value1', 'meta2': 'value2'}
    # 文件上传
    resp = obsClient.putFile(bucketName, objectKey, file_path, metadata, headers)
    print(f"resp: {resp}")
    # 返回码为2xx时，接口调用成功，否则接口调用失败
    if resp.status < 300:
        print('Put File Succeeded')
        print('requestId:', resp.requestId)
        print('etag:', resp.body.etag)
        print('versionId:', resp.body.versionId)
        print('storageClass:', resp.body.storageClass)
        # 获取上传后的文件URL
        if hasattr(resp.body, 'objectUrl') and resp.body.objectUrl:
            file_url = resp.body.objectUrl
            print(f'objectUrl: {file_url}')
        else:
            print('警告: 响应中未找到objectUrl')
    else:
        print('Put File Failed')
        print('requestId:', resp.requestId)
        print('errorCode:', resp.errorCode)
        print('errorMessage:', resp.errorMessage)
except:
    print('Put File Failed')
    print(traceback.format_exc())


async def download_file_with_aiohttp(url: str, save_path: str):
    """
    使用aiohttp.ClientSession下载文件并保存到本地
    
    Args:
        url: 文件的完整访问URL
        save_path: 保存到本地的文件路径
    """
    try:
        # 创建不验证SSL证书的连接器（用于处理自签名证书）
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    # 读取文件内容
                    file_data = await response.read()
                    # 确保保存目录存在
                    save_dir = os.path.dirname(save_path)
                    if save_dir and not os.path.exists(save_dir):
                        os.makedirs(save_dir)
                    # 保存到本地
                    with open(save_path, 'wb') as f:
                        f.write(file_data)
                    print(f'Download File Succeeded')
                    print(f'保存路径: {save_path}')
                    print(f'文件大小: {len(file_data)} 字节')
                    return True
                else:
                    print(f'Download File Failed')
                    print(f'HTTP状态码: {response.status}')
                    return False
    except Exception as e:
        print(f'Download File Failed')
        print(f'错误信息: {str(e)}')
        print(traceback.format_exc())
        return False


# 下载文件示例（使用上传后返回的objectUrl）
if file_url:
    try:
        # 本地保存路径
        local_save_path = 'downloaded_OCR接口说明文档.md'
        
        print(f'\n开始下载文件...')
        print(f'下载URL: {file_url}')
        print(f'保存路径: {local_save_path}')
        
        # 使用asyncio运行异步下载函数
        asyncio.run(download_file_with_aiohttp(file_url, local_save_path))
        
    except Exception as e:
        print('Download File Failed')
        print(traceback.format_exc())
else:
    print('\n跳过下载：未获取到文件URL（上传可能失败）')