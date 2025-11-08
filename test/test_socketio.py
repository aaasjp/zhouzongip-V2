import time
import socketio

sio = socketio.Client(ssl_verify=False)

session_id = '1000000000009999'
user_id = 'songjianpig'

join_params = {
    "session_id": session_id,
    "user_id": user_id
}

leave_params = {
    "session_id": session_id
}

chat_params = {
    'prompt': '介绍一下益师智友',
    'history': [],
    'session_id': session_id,
    'tenant_code': 'xiaomi',
    'collection_name': 'xiaoshou',
    'user_id': user_id
}

disconnect_params = {
    "session_id": session_id
}


@sio.event
def connect():
    print('连接已建立')
    # 调用join方法


# 连接失败的处理
@sio.event
def connect_error(data):
    print("连接失败", data)


@sio.on('message')
def on_message(data):
    print('收到服务器响应:', data)


@sio.event
def disconnect():
    sio.emit('disconnect', disconnect_params)
    print("连接断开")


def join():
    sio.emit('join', join_params)
    print('已调用join方法')


def sent_message():
    sio.emit('chat', chat_params)
    print('已调用chat方法')


def leave():
    sio.emit('leave', leave_params)
    print("离开房间")


sio.connect('ws://106.54.25.147:8802', namespaces=['/'])
time.sleep(3)
join()
time.sleep(3)
sent_message()
time.sleep(10)
leave()
time.sleep(3)
sio.disconnect()




# 等待服务器断开连接
# sio.wait()

# 断开连接
# sio.disconnect()
