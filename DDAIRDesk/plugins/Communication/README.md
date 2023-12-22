<h1 align='center'> DDSocket插件 </h1>

---

项目/产品简介

<p align="center"> 
<img src="", width="640">
</p>
<p align="center">测试结果图片或视频<p align="center">


## 目录
- [目录](#目录)
- [更新日志](#更新日志)
- [部署环境](#部署环境)
- [安装说明](#安装说明)
- [使用说明](#使用说明)
- [预告内容](#预告内容)
- [参考文档](#参考文档)



## 更新日志

|        版本号 | 更新内容 |
|-----------:|--|
| 0.1.221114 | socket插件框架搭建（未完善和测试） |


## 部署环境
（这里写基础环境，包括如下，其他python包写到requirments）


## 安装说明

```shell

```
---

## 使用说明

这里写运行demo等文件的脚本示例，或者启动流程等

```
conf = read_yaml("socket_example_conf.yaml","udp_server")
if conf:
    dd_sock = DDSocket()
    type = dd_sock.socket_type
    # 根据配置文件设置socket属性
    sock_pairs = dd_sock.set_sock(set_pairs=[
                {"sock_type":type.UDP_SERVER, "addr":tuple(conf["addr"])},
                # {"sock_type":"tcp_client", "addr":("172.27.3.111",8004)}
                ])
                
    # 开启发送或接受线程（可只开一个）
    dd_sock.udp_server.start_send_thread()
    dd_sock.udp_server.start_recv_thread()
    
    # 接受数据
    recv_data = dd_sock.udp_server.get_data()
    # 发送数据
    dd_sock.udp_server.set_data(b'hello')
```


## 预告内容

- 心跳机制
  
