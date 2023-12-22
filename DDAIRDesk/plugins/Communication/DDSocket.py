# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDSocket.py
# @Author     : MJJ
# @Version    : 0.X.23XXXX
# @Date       : 3/3/2023
# @Description:
# @Upadate    :
# @Software   : PyCharm

from enum import Enum
import time
import socket
from queue import Queue
import threading
from threading import Thread, Event
from loguru import logger


class DDSocketBase:
    '''
    Socket基类
    '''

    def __init__(self, sock_type, addr):
        """

        Args:
            sock_type: socket类型
            addr: ("ip",port)
        """
        self.heart_msg = b'\xdd\x01'  # 心跳数据
        self.reg_msg = b'\xdd\x02'  # 注册数据
        self.discon_msg = b'\xdd\x03'  # 断开连接数据
        self.q_b_rev = Queue()  # 接收数据队列
        self.q_b_send = Queue()  # 发送消息队列

        self._send_thread = None
        self._recv_thread = None
        self._heart_beat_thread = None

        self._recv_event = Event()  # 控制接收消息线程
        self._send_event = Event()  # 控制发送消息线程
        self._heart_event = Event()
        self._has_length = False  # 接收消息是否包含长度信息
        self._recv_len = 16

        self.sock_type = sock_type
        self.addr = addr  # 连接的("ip",port)
        self.dist_addr = None
        if "tcp" in sock_type.name.lower():
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 在绑定前调用setsockopt让套接字允许地址重用
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        elif "udp" in sock_type.name.lower():
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 解决端口被占用
        self.conn = None  # 连接的socket
        self.reconnect_interval = 3  # 初始重连间隔（秒）
        self.max_reconnect_attempts = 8  # 最大重连尝试次数（8次保证10分钟之内的重连）
        self.conn_lock = threading.Lock()  # 创建线程锁

    def _connect(self):
        '''
        连接
        '''
        pass

    def _reconnect(self):
        '''
        断线重连
        '''
        pass

    def _is_guardianship(self, recv):
        """
        检查接收数据类型是否为通信监护数据

        Args:
            recv: 接收到的信息

        Returns: 如果是心跳/注册/关闭数据，返回True，是正常数据返回False

        """
        if recv.decode("utf8", "ignore") == self.heart_msg.decode("utf8", "ignore"):
            print("心跳包")
            return True
        elif recv.decode("utf8", "ignore") == self.discon_msg.decode("utf8", "ignore"):
            logger.info("[tcp server] Receive a disconnect request from the client.")
            self._reconnect()
            return True
        elif recv.decode("utf8", "ignore") == self.reg_msg.decode("utf8", "ignore"):
            print("注册包")
            self.conn.send(bytes("Connected", encoding="utf-8"))
            return True
        return False

    def _recv(self):
        """

        Returns:

        """
        while True:
            time.sleep(0.01)
            if self._recv_event.is_set():
                break
            try:
                if self.conn is not None:
                    recv, addr = self.conn.recvfrom(self._recv_len)
                    self.dist_addr = addr
                    if not recv:
                        logger.warning(f"[DDSocket {self.sock_type}] The client is offline.")
                        self._reconnect()
                    if not self._is_guardianship(recv):
                        # recv_length = int.from_bytes(recv, byteorder="big")
                        # recv_length = length.decode()
                        if self._has_length:
                            if int.from_bytes(recv, byteorder="big") != 0:
                                recv_length = int(recv)
                                if recv_length > 0:
                                    print("recv length:", recv_length)
                                    self.q_b_rev.put(self._recv_all(recv_length))  # 根据获得的文件长度，获取图片文件
                                    print("recv data over.")
                        else:
                            self.q_b_rev.put(recv)

                else:
                    continue
            except socket.error:  # 掉线等待新的客户端连接
                logger.error(f"[DDSocket {self.sock_type}] Socket error occur.")
                self._reconnect()
            except Exception as e:
                logger.error(f"[DDSocket {self.sock_type}] Other error occur while receiving.{e}")
                self._reconnect()

    def _recv_all(self, recv_length):
        """

        Args:
            recv_length: 需要接收的全部信息

        Returns:

        """
        buf = b''  # buf是一个byte类型
        newbuf = b''
        while recv_length:
            # 接受TCP套接字的数据。数据以字符串形式返回，count指定要接收的最大数据量.
            try:
                newbuf, addr = self.conn.recvfrom(recv_length)
                self.dist_addr = addr
            except socket.error:  # 掉线等待新的客户端连接
                logger.error(f"[DDSocket {self.sock_type}] Socket error occur.")
                self._reconnect()
            except Exception as e:
                logger.error(f"[DDSocket {self.sock_type}] Other error occur while receiving all.{e}")
                self._reconnect()
            if not newbuf: return None
            if not self._is_guardianship(newbuf):
                buf += newbuf
                recv_length -= len(newbuf)
        return buf

    def _send(self):
        t1 = time.time()
        while True:
            if self._send_event.is_set():
                time.sleep(0.01)
                break
            if (not self.q_b_send.empty()) and (self.conn is not None):
                try:
                    self.conn.sendall(self.q_b_send.get())
                    if (time.time() - t1) > 30:  # 每隔10秒打印一次
                        t1 = time.time()
                        logger.info(f"[DDSocket {self.sock_type}] Send.")
                except socket.error:  # 掉线重连
                    logger.error(f"[DDSocket {self.sock_type}] Socket send Error occur.")
                    self._reconnect()
                except Exception as e:
                    logger.error(f"[DDSocket {self.sock_type}] Other error occur while sending.{e}")
                    self._reconnect()
            time.sleep(0.01)

    def get_data(self):
        """
        非阻塞获取消息队列里接收到的信息
        Returns:
            接收到的信息

        """
        if self.q_b_rev.empty():
            return None
        return self.q_b_rev.get()

    def get_data_blocking(self):
        """
        阻塞获取消息队列里接收到的信息
        Returns:

        """
        return self.q_b_rev.get()

    def set_data(self, msg):
        """
        将发送信息塞入到消息队列里
        Args:
            msg: 发送信息，已编码好

        Returns:
            True: 设置成功
            False: 设置失败

        """
        try:
            self.q_b_send.put(msg)
            return True
        except Exception:
            return False

    def start_recv_thread(self, has_length: bool = False, recv_len: int = 1024):
        """
        开启接收信息线程。
        Args:
            has_length: 包含长度信息的接收（长度与数据分离）
            recv_len: 接收长度，has_length = False时才赋值，表示真实数据长度，
                    否则定义长度信息本身长16位。

        Returns:
            True: 成功
            False: 失败

        """
        try:
            self._has_length = has_length
            if not self._has_length:
                self._recv_len = recv_len
            self._recv_thread = Thread(target=self._recv, daemon=True)
            self._recv_thread.start()
            return True
        except Exception:
            print(self._has_length)
            return False

    def start_send_thread(self):
        """
        开始发送信息线程。
        Returns:
            True: 成功
            False: 失败

        """
        try:
            self._send_thread = Thread(target=self._send, daemon=True)
            self._send_thread.start()
            return True
        except threading.ThreadError:
            print("线程创建或启动错误")
            return False
        except RuntimeError:
            print("线程已经在运行或尝试重新启动线程")
            return False

    def _heart_beat(self):
        while True:
            self.set_data(self.heart_msg)
            time.sleep(30)

    def start_heart_thread(self):
        """
        每30秒发送一次消息保证长连接
        Returns:

        """
        time.sleep(3)
        if self._send_thread is None:
            self.start_send_thread()
        elif not self._send_thread.is_alive():
            self.start_send_thread()
        try:
            self._heart_beat_thread = Thread(target=self._heart_beat, daemon=True)
            self._heart_beat_thread.start()
            return True
        except threading.ThreadError:
            print("线程创建或启动错误")
            return False
        except RuntimeError:
            print("线程已经在运行或尝试重新启动线程")
            return False

    def close(self):
        self.conn.close()
        self.sock.close()
        self._recv_event.set()
        self._send_event.set()
        self._heart_event.set()
        if self._send_thread is not None:
            while self._send_thread.is_alive():
                time.sleep(0.01)
        if self._recv_thread is not None:
            while self._recv_thread.is_alive():
                time.sleep(0.01)
        if self._heart_beat_thread is not None:
            while self._heart_beat_thread.is_alive():
                time.sleep(0.01)
        logger.info(f"[DDSocket {self.sock_type}] Exit.")


class DDTCPServer(DDSocketBase):
    '''
    TCP服务器
    '''

    def __init__(self, sock_type, bind_addr, listen_num):
        """

        Args:
            sock_type: socke类型
            bind_addr: ("ip",port)
            listen_num: 监听客户端个数
        """
        super(DDTCPServer, self).__init__(sock_type, bind_addr)
        self.sock.bind(bind_addr)
        self.sock.listen(listen_num)
        logger.info("TCP Server is listening on ", bind_addr)
        self.conn = None
        self.client_addr = None
        conn_thread = Thread(target=self._connect, daemon=True)
        conn_thread.start()

    def _connect(self):
        try:
            with self.conn_lock:
                self.conn, self.client_addr = self.sock.accept()
                logger.info(f"[DDSocket {self.sock_type}] Connect from:{str(self.client_addr)}")
        except socket.error as msg:
            logger.error(f"[DDSocket {self.sock_type}] {msg}")

    def _reconnect(self):
        logger.info(f"[DDSocket {self.sock_type}] Disconnect from:{str(self.client_addr)}")
        with self.conn_lock:
            self.conn.close()
            self.conn, self.client_addr = None, None
        self._connect()


class DDTCPClient(DDSocketBase):
    '''
    TCP客户端
    '''

    def __init__(self, sock_type, addr):
        super(DDTCPClient, self).__init__(sock_type, addr)
        self.reconnect_interval = 3
        conn_thread = Thread(target=self._connect, daemon=True)
        conn_thread.start()

    def _connect_old(self):
        """
        尝试建立连接
        Returns:

        """
        while True:
            try:
                self.sock.connect(self.addr)
                self.conn = self.sock
                logger.info(f"[DDSocket {self.sock_type}] Connected with server.")
                break  # 跳出循环，连接成功后退出
            except socket.error as msg:
                logger.warning(f"[DDSocket {self.sock_type}] {msg}")
                logger.info(f"[DDSocket {self.sock_type}] Reconnect...")
                time.sleep(self.reconnect_interval)

    def _reconnect_old(self):
        logger.info(f"[DDSocket {self.sock_type}] You have disconnected. Trying to reconnect...")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            logger.error(e)
        self._connect()

    def _connect(self):
        """
        尝试建立连接
        Returns:

        """
        for attempt in range(self.max_reconnect_attempts):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 尝试重新连接
                self.sock.connect(self.addr)
                with self.conn_lock:
                    self.conn = self.sock
                logger.info(f"[DDSocket {self.sock_type}] Connected successfully.")
                break
            except socket.error as e:
                wait_time = self.reconnect_interval * (2 ** attempt)
                logger.error(f"[DDSocket {self.sock_type}] Connect attempt failed: {e}")
                logger.warning(
                    f"[DDSocket {self.sock_type}] Attempting to reconnect, attempt {attempt + 1}/{self.max_reconnect_attempts}, Waiting for {wait_time} seconds......")
                time.sleep(wait_time)  # 指数退避策略
        else:
            logger.error(f"[DDSocket {self.sock_type}] Maximum reconnect attempts reached. Giving up.")

    def _reconnect(self):
        """
        断线重连，增加指数退避策略
        Returns:

        """
        logger.warning(f"[DDSocket {self.sock_type}] Disconnected, attempt Reconnect...")
        self._connect()

    def __del__(self):
        # super(DDTCPClient, self).__del__()
        pass


class DDUDPClient(DDSocketBase):
    '''
    UDP客户端
    '''

    def __init__(self, sock_type, addr):
        super(DDUDPClient, self).__init__(sock_type, addr)
        self.reconnect_interval = 3
        conn_thread = Thread(target=self._connect, daemon=True)
        conn_thread.start()

    def _connect(self):
        while True:
            try:
                self.sock.connect(self.addr)
                with self.conn_lock:
                    self.conn = self.sock
                logger.info(f"[DDSocket {self.sock_type}] Connected with server.")
                break  # 跳出循环，连接成功后退出
            except socket.error as msg:
                logger.warning(f"[DDSocket {self.sock_type}] {msg}")
                logger.info(f"[DDSocket {self.sock_type}] Reconnect...")
                time.sleep(self.reconnect_interval)
        # 下面代码当一直连接不上时，会出现栈溢出（递归太深分配内存）
        # try:
        #     self.sock.connect(self.addr)
        #     self.conn = self.sock
        #     logger.info(f"[DDSocket {self.sock_type}] Connected with server.")
        # except socket.error as msg:
        #     logger.warning(f"[DDSocket {self.sock_type}] {msg}")
        #     logger.info(f"[DDSocket {self.sock_type}] Reconnect...")
        #     time.sleep(self.reconnect_interval)
        #     self._connect()

    def _reconnect(self):
        logger.info(f"[DDSocket {self.sock_type}] You have disconnected. Trying to reconnect...")
        self._connect()

    def __del__(self):
        # super(DDUDPClient, self).__del__()
        pass


class DDUDPServer(DDSocketBase):
    '''
    UDP服务器
    '''

    def __init__(self, sock_type, bind_addr):
        super(DDUDPServer, self).__init__(sock_type, bind_addr)
        self.sock.bind(bind_addr)
        self.conn = self.sock

    def _send(self):
        t1 = time.time()
        while True:
            if self._send_event.is_set():
                break
            if (not self.q_b_send.empty()) and self.conn and self.dist_addr:
                try:
                    self.conn.sendto(self.q_b_send.get(), self.dist_addr)
                    self.conn.sendall(self.q_b_send.get())
                    if (time.time() - t1) > 30:
                        t1 = time.time()
                        logger.info(f"[DDSocket {self.sock_type}] Send successful.")
                except socket.error:  # 掉线重连
                    logger.error(f"[DDSocket {self.sock_type}] Socket send Error occur.")
                    self._reconnect()
                except Exception:
                    logger.error(f"[DDSocket {self.sock_type}] Other error occur while sending.")
                    self._reconnect()
            time.sleep(0.01)

    def start_send_thread(self):
        """
        开始发送信息线程。
        Returns:
            True: 成功
            False: 失败

        """
        try:
            self.start_recv_thread()
            self._send_thread = Thread(target=self._send, daemon=True)
            self._send_thread.start()
            return True
        except threading.ThreadError:
            print("线程创建或启动错误")
            return False
        except RuntimeError:
            print("线程已经在运行或尝试重新启动线程")
            return False


class DDSocketType(Enum):
    '''
    Socket类型
    '''
    TCP_SERVER = 0
    TCP_CLIENT = 1
    UDP_SERVER = 2
    UDP_CLIENT = 3


class DDSocket:
    '''
    Socket工厂类
    '''

    def __init__(self):
        """
        Examples:
            dd_sock = DDSocket()
            type = dd_sock.socket_type
            # 注意addr是服务器的
            sock_pairs = dd_sock.set_sock(set_pairs=[
                        {"sock_type":type.TCP_SERVER, "addr":("127.0.0.1",8004)},
                        {"sock_type":type.TCP_CLIENT, "addr":("127.0.0.1",8004)}])
            dd_sock.tcp_server.start_recv_thread()
            dd_sock.tcp_client.start_send_thread()
            ...
            recv_data = dd_sock.tcp_server.get_data()
            if recv_data:
                # data process

            dd_sock.tcp_client.set_data(msg)
        """
        # 暂时无心跳
        self.tcp_server = DDTCPServer
        self.udp_server = DDUDPServer
        self.tcp_client = DDTCPClient
        self.udp_client = DDUDPClient
        self.socket_type = DDSocketType

    def set_sock(self, set_pairs: list = []):
        """ Sets the sock to be used.

        Args:
            set_pairs: [{"sock_type":self.socket_type.TCP_CLIENT, "addr":("ip",port)}],
                        socket类型
                        "tcp_server","tcp_client",
                        "udp_server","udp_client"

        Returns:
            sock_pairs: {"tcp_server":self.tcp_server,"udp_server":self.udp_server,
                        "tcp_client":self.tcp_client, "udp_client":self.udp_client}
        """
        # TODO: 最大连接客户端个数设置
        # TODO：心跳机制设置
        for pair in set_pairs:
            if pair["sock_type"] == DDSocketType.TCP_SERVER:
                self.tcp_server = DDTCPServer(pair["sock_type"], pair["addr"], 1)
            elif pair["sock_type"] == DDSocketType.UDP_SERVER:
                self.udp_server = DDUDPServer(pair["sock_type"], pair["addr"])
            elif pair["sock_type"] == DDSocketType.TCP_CLIENT:
                self.tcp_client = DDTCPClient(pair["sock_type"], pair["addr"])
            elif pair["sock_type"] == DDSocketType.UDP_CLIENT:
                self.udp_client = DDUDPClient(pair["sock_type"], pair["addr"])
            else:
                print("type error.")
        sock_pairs = {"tcp_server": self.tcp_server, "udp_server": self.udp_server,
                      "tcp_client": self.tcp_client, "udp_client": self.udp_client}
        return sock_pairs

    def close(self):
        # 插件销毁
        print("Waiting for resources to be released")
        if isinstance(self.tcp_server, DDTCPServer):
            self.tcp_server.close()
            print("DDTCPServer Closed!")
        if isinstance(self.tcp_client, DDTCPClient):
            self.tcp_client.close()
            print("DDTCPClient Closed!")
        if isinstance(self.udp_server, DDUDPServer):
            self.udp_server.close()
            print("DDUDPServer Closed!")
        if isinstance(self.udp_client, DDUDPClient):
            self.udp_client.close()
            print("DDUDPClient Closed!")
        return True


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDSocket
