import requests
import json

base_url = 'http://172.17.10.144:8802/'
api_key = '2024_hello_ai'
session_id='20232013123123-10000002'


def post_request(url, data):
    try:
        json_data = json.dumps(data)
        response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json_data)
        response.raise_for_status()  # 检查请求是否成功
        return response.json()  # 返回JSON格式的响应内容
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"OOps: Something Else: {err}")


def test_generate_session_id():
    print('测试创建session_id接口')
    api_url = base_url + 'generate_session_id'
    data = {
        'api_key': api_key
    }
    result = post_request(api_url, data)
    print(result)


def test_get_recommend_questions(session_id):
    print('测试获取推荐问题接口')
    api_url = base_url + 'get_recommend_questions'
    data = {
        'session_id': session_id,
        'api_key': api_key
    }
    result = post_request(api_url, data)
    print(result)



# 使用示例
if __name__ == "__main__":
    test_generate_session_id()
    test_get_recommend_questions(session_id)


