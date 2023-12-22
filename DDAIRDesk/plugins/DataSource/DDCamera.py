# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDCamera.py
# @Author     : MJJ
# @Version    : 0.X.23XXXX
# @Date       : 5/29/2023
# @Description: 加载视频插件
# @Upadate    : 
# @Software   : PyCharm


import time
from queue import Queue
from threading import Thread, Event

import cv2
from loguru import logger
from DDAIRDesk.tools.read_yaml import read_yaml
from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin


class DDCamera(DDBasePlugin):
    """获取Usb/网络摄像头类
    单独线程获取图片数据，存入队列，通过get_frame方法从外部获取
    Examples:
            stream = DDCamera()  # 创建迭代器
            for img in stream:         # 从队列中拿视频帧
                if img is None:
                    continue
                # HERE IS YOUR CODE FOR PROCESS
                if cv2.waitKey(1) == 27:
                    break
            del stream  # 析构
    """

    def __init__(self, yaml_path):
        """初始化

        """
        super(DDCamera, self).__init__()
        try:
            self.config = read_yaml(yaml_path, 'DDCamera')
            self.type = self.config['type']
            self.width = 640 if self.config['width'] == "None" else self.config['width']
            self.index = self.config['index']
            if isinstance(self.index, str):
                self.index = eval(self.index) if self.index.isnumeric() else self.index
        except FileNotFoundError as e:
            print("配置文件不存在:", e)
            exit()
        except KeyError as e:
            print(f"配置文件中DDCamera出错!({e})")
            exit()
        self.cap = cv2.VideoCapture(self.index)
        if self.type == "webcam":
            self.cap.set(3, self.width)
        self.event = Event()
        self.q_frame = Queue(maxsize=2)
        self.thread = Thread(target=self.update, daemon=True)


    def reconnect(self):
        """设备断线重连

        Returns:

        """
        print("DDCamera reconnect...")
        ret = False
        while not ret:
            self.cap.release()
            self.cap = cv2.VideoCapture(self.index)
            if self.type == "webcam":
                self.cap.set(3, self.width)
            if self.cap.isOpened():
                ret, img = self.cap.read()
            else:
                time.sleep(0.1)
        print("DDCamera connected!")

    def update(self):
        """线程运行函数

        Returns:

        """
        print("DDCamera start")
        while True:
            if self.event.is_set():
                break
            ret, img = self.cap.read()
            if ret:
                self.q_frame.put(img)  # 默认阻塞方式，直到队列不为空时才Put进去
                # try:
                #     # 将声音传到线程内
                #     self.q_frame.put_nowait(img)  # 非阻塞，默认阻塞方式，直到队列不为空时才Put进去
                # except Exception as e:
                #     time.sleep(0.01)
                #     logger.warning("DDCamera队列已满，当前数据丢失.")
                # while self.q_frame.full():
                # # while self.q_frame.qsize() > 1:  # 受不明原因（python版本？平台？）queue的qsize未实现
                #     self.q_frame.get()
                # self.q_frame.put(img)
            else:
                self.reconnect()

    def __call__(self):
        self.thread.start()

    def __iter__(self):
        return self

    def __next__(self):
        return self.q_frame.get()
        # if not self.q_frame.empty():
        # # if self.q_frame.qsize() > 0:  # 偶尔报错，缺少虚基类的派生方法
        #     return self.q_frame.get()
        # # print(self.q_frame.qsize())
        # return None

    def __del__(self):
        self.event.set()
        time.sleep(0.01)
        print(f"Camera thread alive? {self.thread.is_alive()}")
        self.cap.release()
        print("DDCamera closed!")


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDCamera