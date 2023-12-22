# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : test.py.py
# @Author     : MJJ
# @Version    :
# @Date       : 2022/11/15 20:20
# @Description: 可列出参考连接，如mediapipe的demo连接； 模块功能等
# @Update     :
# @Software   : PyCharm
import time

from DDSocket import DDSocket
from tools.read_yaml import read_yaml


conf = read_yaml("socket_example_conf.yaml","tcp_client")
if conf:
    dd_sock = DDSocket()
    type = dd_sock.socket_type
    sock_pairs = dd_sock.set_sock(set_pairs=[
                # {"sock_type":type.UDP_SERVER, "addr":tuple(conf["addr"])},
                {"sock_type":type.TCP_CLIENT, "addr":tuple(conf["addr"])}
                ])
    dd_sock.tcp_client.start_send_thread()
    dd_sock.tcp_client.start_recv_thread()
    # recv_data = dd_sock.tcp_server.get_data()

    recv_data = dd_sock.tcp_client.get_data()
    while not recv_data:
        recv_data = dd_sock.tcp_client.get_data()
    print(recv_data.decode())
    recv_data = dd_sock.tcp_client.get_data()
    while not recv_data:
        recv_data = dd_sock.tcp_client.get_data()
    print(recv_data.decode())
    while True:
        dd_sock.tcp_client.set_data(b'hello')
        time.sleep(5)



