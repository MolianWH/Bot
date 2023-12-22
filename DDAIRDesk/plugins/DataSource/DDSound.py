# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDSound.py
# @Author     : Dawei TANG
# @Version    :
# @Date       : 2022/11/22 11:27
# @Description: 可列出参考连接，如mediapipe的demo连接； 模块功能等
# @Upadate    : 2023/8/11 BUG修复：队列阻塞不再get
# @Software   : PyCharm

from queue import Queue
from threading import Thread

import pyaudio
from loguru import logger

from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin
from DDAIRDesk.tools.read_yaml import read_yaml
from DDAIRDesk.tools.ddio import wait_interval
import time


@wait_interval(5)
def logger_interval(text):
    """
    定时打印。每隔5秒打印一次，防止频繁打印
    Args:
        text: 输入文本

    """
    logger.warning(text)


class DDSound(DDBasePlugin):
    """读取语音获取文字
    Examples:
            stream = DetectSound()  # 创建迭代器
            for words in stream:         # 从队列中拿视频帧
                if words is None:
                    continue
                # HERE IS YOUR CODE FOR PROCESS
                if cv2.waitKey(1) == 27:
                    break
            del stream  # 析构

    """

    def __init__(self, yaml_path):
        super(DDSound, self).__init__()
        try:
            self.config = read_yaml(yaml_path, 'DDSound')
            # 音频流截取设置
            self.chunk = self.config['chunk']  # Record in chunks of 1024 samples
            self.channels = self.config['channels']  # 声道数量
            self.sample_rate = self.config['sample_rate']  # 44100 samples per second
            self.device_name = self.config['device_name']
        except Exception as e:
            print("配置文件中DDSpeech出错!", e)
            exit()

        self.p = None
        self.stream = None
        self.q_sound = Queue(maxsize=2)
        self.thread = Thread(target=self.update, daemon=True)
        self.chunk_id = 0

        # 开启音频流
        try:
            self.open_stream()
        except Exception as e:
            logger.error(f"Initial connection to audio device failed: {e}")

    def open_stream(self):
        """
        开启音频流
        Returns:

        """
        # 重置 PyAudio 实例
        if self.p is not None:
            self.p.terminate()
        self.p = pyaudio.PyAudio()

        # 查找指定音频输入编号
        self.device_index = 0

        print("可用音频输入设备列表：")
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:
                print(f"设备{i}:{device_info['name']}")
                if device_info.get('name', '') == self.device_name:
                    self.device_index = device_info.get('index')
                    print(f"已选择设备: 设备{self.device_index}: {self.device_name}")
                    break
        if self.device_index == 0:
            print("启用默认音频设备0：", self.p.get_device_info_by_index(0).get('name', ''))

        self.stream = self.p.open(format=pyaudio.paInt16,
                                  rate=self.sample_rate,
                                  channels=self.channels,
                                  input=True,
                                  input_device_index=self.device_index,
                                  frames_per_buffer=self.chunk)

    def update(self):
        print('DDSound Start!')

        while 1:
            chunk = b''
            try:
                chunk = self.stream.read(self.chunk)
            except Exception as e:
                logger.error(e)
                self.reconnect_stream()
            self.chunk_id += 1
            data = {'chunk': chunk, 'chunk_id': self.chunk_id}
            try:
                # 将声音传到线程内
                self.q_sound.put_nowait(data)  # 非阻塞，默认阻塞方式，直到队列不为空时才Put进去
            except Exception as e:
                logger_interval("DDSound队列已满，当前数据丢失.")
                # logger.warning("DDSound队列已满，当前数据丢失.")
            DDBasePlugin.DDPluginDataFlow['DDSound'] = data

    def reconnect_stream(self, max_retries: int = 5, delay: int = 5) -> None:
        """
        尝试重新连接音频输入设备
        Args:
            max_retries: 最大重连次数，默认5次
            delay: 重连间隔，单位秒，默认5秒

        Returns:

        """
        for attempt in range(max_retries):
            try:
                self.open_stream()
                logger.info("Reconnected to audio device.")
                break
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1}/{max_retries} failed: {e}")
                time.sleep(delay)
        else:
            logger.critical("Failed to reconnect after several attempts.")

    def __call__(self):
        self.thread.start()

    def __iter__(self):
        return self

    def __next__(self):
        return self.q_sound.get()
        # if not self.q_sound.empty():
        #     # if self.q_sound.qsize() > 0:  # 偶尔报错，缺少虚基类的派生方法
        #     return self.q_sound.get()
        # return None

    def __del__(self):
        if self.stream:
            self.stream.stop_stream()  # Stop and close
            self.stream.close()
        self.p.terminate()  # Terminate the PortAudio interface
        print("DDSound closed!")


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDSound
