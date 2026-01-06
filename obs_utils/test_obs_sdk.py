from obs import ObsClient
import os
import traceback

# 推荐通过环境变量获取AKSK，这里也可以使用其他外部引入方式传入，如果使用硬编码可能会存在泄露风险
# 您可以登录访问管理控制台获取访问密钥AK/SK，获取方式请参见https://support.huaweicloud.com/usermanual-ca/ca_01_0003.html
ak = "SNEIPXFWBJMMXE8IH4RL"
sk = "P5RN40MY9jyuFV6WlbiGsD0BsSgltwkzTwZrPjxf"
# 【可选】如果使用临时AKSK和SecurityToken访问OBS，则同样推荐通过环境变量获取
# security_token = os.getenv("SecurityToken")
# server填写Bucket对应的Endpoint, 这里以华北-北京四为例，其他地区请按实际情况填写
server = "https://203.0.113.1"
# 创建obsClient实例
# 如果使用临时AKSK和SecurityToken访问OBS，需要在创建实例时通过security_token参数指定securityToken值
obsClient = ObsClient(access_key_id=ak, secret_access_key=sk, server=server)
try:
    bucketName="gaoguanip-files"
    #判断桶是否存在
    resp = obsClient.headBucket(bucketName)
    # 返回码为2xx时，接口调用成功，否则接口调用失败
    if resp.status < 300:
        print('Head Bucket Succeeded')
        print('Bucket exists')
    elif resp.status == 404:
        print('Head Bucket Failed')
        print('Bucket does not exist')
    else:
        print('Head Bucket Failed')
        print('status:', resp.status)
        print('requestId:', resp.requestId)
        print('errorCode:', resp.errorCode)
        print('errorMessage:', resp.errorMessage)
except:
    print('Head Bucket Failed')
    print(traceback.format_exc())