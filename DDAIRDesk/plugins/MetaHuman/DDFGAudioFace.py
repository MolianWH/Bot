# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDFGAudioFace.py
# @Author     : MJJ
# @Version    :
# @Date       : 2023/1/4 20:43
# @Description: FaceGood版AudioFace
# @Update     :
# @Software   : PyCharm

import os
import sys
import time
import threading
from threading import Lock, Thread
from queue import Queue
from random import choice
import numpy as np
import pandas as pd
import pyaudio
from loguru import logger
from pylivelinkface import PyLiveLinkFace, FaceBlendShape

from DDAIRDesk.plugins.MetaHuman.utils.tensorflow.input_wavdata_output_lpc import c_lpc, get_audio_frames
from DDAIRDesk.plugins.MetaHuman.utils.tensorflow.input_lpc_output_weight import WeightsAnimation
from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin
from DDAIRDesk.tools.read_yaml import read_yaml

sys.path.append(".")
sys.path.append("..")

MAPPING = {
    'JawOpen': [27],
    'MouthDimpleLeft': [7],
    'MouthDimpleRight': [8],
    'MouthFunnel': [9, 10, 11, 12],
    'MouthLowerDownLeft': [19],
    'MouthLowerDownRight': [20],
    'MouthPressLeft': [23],
    'MouthPressRight': [24],
    'MouthPucker': [25, 26],
    'MouthRollLower': [28, 29],
    'MouthRollUpper': [30, 31],
    # 'MouthShrugLower': [1],
    'MouthShrugUpper': [6],
    'MouthSmileLeft': [13],
    'MouthSmileRight': [14],
    'MouthStretchLeft': [17],
    'MouthStretchRight': [18],
    'MouthUpperUpLeft': [32],
    'MouthUpperUpRight': [33],
    'NoseSneerLeft': [34],
    'NoseSneerRight': [35],
}


# *******************************************
class SoundAnimation:
    '''
    第三方FaceGood自带的推理模块
    '''

    def __init__(self, model_path, cpus=1, input_nums=30):
        self.cpus = cpus
        self.input_nums = input_nums
        self.init_multiprocessing()
        self.flag_start = False
        pb_weights_animation = WeightsAnimation(model_path)
        self.get_weight = pb_weights_animation.get_weight

    def __del__(self):
        if self.flag_start:
            self.stop_multiprocessing()

    def worker(self, q_input, q_output, i):
        print("the cpus number is:", i)
        while True:
            input_data = q_input.get()
            for output_wav in input_data:
                output_lpc = c_lpc(output_wav)
                output_data = self.get_weight(output_lpc)
                q_output.put(output_data)

    def init_multiprocessing(self):
        self.q_input = [Queue() for i in range(0, self.cpus)]
        self.q_output = [Queue() for i in range(0, self.cpus)]
        self.process = []
        for i in range(0, self.cpus):
            self.process.append(
                threading.Thread(target=self.worker, args=(self.q_input[i], self.q_output[i], i)))
            # Process(target=worker, args=(self.q_input[i], self.q_output[i], i)))

    def start_multiprocessing(self):
        self.flag_start = True
        for i in range(0, self.cpus):
            self.process[i].setDaemon(True)
            # self.process[i].daemon = True
            self.process[i].start()

    def stop_multiprocessing(self):
        for i in range(0, self.cpus):
            self.process[i].terminate()

    def input_frames_data(self, input_date):
        input_data_nums = [input_date[i:i + self.input_nums] for i in range(0, len(input_date), self.input_nums)]
        self.flag_nums = len(input_data_nums)
        for i in range(0, self.cpus):
            self.q_input[i].put(input_data_nums[i::self.cpus])

    def yield_output_data(self):
        num = 0
        flag_end = True
        while flag_end:
            for i in range(0, self.cpus):
                if num == self.flag_nums:
                    flag_end = False
                    break
                data_output = self.q_output[i].get()
                for data in data_output:
                    yield data
                num += 1


class DDFGAudioFace(DDBasePlugin):
    '''
    语音转bs动画插件主入口
    '''

    def __init__(self, yaml_path):
        super(DDFGAudioFace, self).__init__()
        # 读取配置文件
        try:
            self.config = read_yaml(yaml_path, 'DDFGAudioFace')
            self.model_path = self.config.get('model_path', None)
            self.standby_dir = self.config.get('standby_dir', None)
            self.sequence_path = self.config.get('sequence_path', None)
            self.nchannels = self.config.get('nchannels', 1)
            self.rate = self.config.get('rate', 16000)
            cpu_thread = self.config.get('cpu_thread', 2)
            cpu_frames = self.config.get('cpu_frames', 20)
            self.fps = self.config.get("fps", 45)  # 通信接口
            self.standby_duration = self.config.get('standby_duration', 10)
            self.ending_duration = self.config.get("ending_duration", 5)  # 闭嘴动作持续帧数
            self.waiting_error = self.config.get("waiting_error", 0.1)
            self.is_auto_play = self.config.get("auto_play", True)  # 是否自动播放音频
        except FileNotFoundError as e:
            print(f"配置文件{yaml_path}不存在：{e}")
            exit()
        except KeyError as e:
            print(f"配置文件{yaml_path}中DDFGAudioFace出错!{e}")
            exit()

        # 获取动画列表和序列数据
        try:
            self.standby_list = self.get_file_list(self.standby_dir)
        except Exception as e:
            print(f"读取动画序列出错。请检查目录{self.standby_dir}.\n{e}")
        self.seq_data = pd.read_hdf(self.sequence_path, 'data').values.astype(
            np.float64)  # 说话时补充的动作序列数据
        self._seq_name_speech = ["HeadYaw", "HeadPitch", "HeadRoll", "EyeBlinkLeft", "EyeBlinkRight"]  # 说话时补充的数据名

        # 通用状态变量复制
        self.standby_start_time = time.time()
        self.speed_play = 1.0 / self.fps
        self.nframe = 1
        self.stop = False  # wav生成动画是否停止
        self.event_bs_play = threading.Event()
        self.event_bs_play.set()  # 默认开启
        self.audio_play_time = time.time()
        self.lock = Lock()
        self.q_tts_wav = Queue(maxsize=1)

        # 对象创建
        self.sound_animation = SoundAnimation(self.model_path, cpu_thread, cpu_frames)

        # 音频播放（公有）
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=self.p.get_format_from_width(2),
                                  channels=1,
                                  rate=24000,
                                  output=True)

    def load_model(self):
        """
        加载模型，开启线程
        Returns:

        """
        if self.is_auto_play:
            self.thread_audio = Thread(target=self.play_audio)
            self.thread_audio.start()
        self.sound_animation.start_multiprocessing()
        print("DDFGAudioFace Started! Now waiting wav data...")

    def __call__(self, data):
        """

        Args:
            data: 音频数据，字节

        Returns:
            audio_bs: 脸部37个blendshape结果动画帧迭代器

        """
        role = data.get("role", "")
        msg_txt = data.get("content", "")
        b_wav_data = data.get("wav_stream", b'')
        # 插件功能实现
        self.stop = False
        for i in range(0, self.sound_animation.cpus):  # 清除缓存
            self.sound_animation.q_output[i].queue.clear()

        zero_bs_dict = self.get_bs_dict(np.zeros((37,), dtype=np.float32))
        voice = np.frombuffer(b_wav_data, dtype=np.int16)
        input_data = get_audio_frames(voice, rate=16000)
        # 音频转bs序列
        try:
            self.sound_animation.input_frames_data(input_data)
            is_first = True
            f_num = 0
            f_btime = time.time()
            bs_weight = self.sound_animation.yield_output_data()
            for weight in bs_weight:
                f_num += 1
                if is_first:
                    logger.info("BS状态判断。")
                    if self.is_auto_play:
                        # logger.info("BS设置播放状态。")
                        self.event_bs_play.wait()
                        with self.lock:
                            self.event_bs_play.clear()
                            # logger.info("BS重置播放状态。")
                        # 通知音频开始播放
                        self.q_tts_wav.put(b_wav_data)
                    is_first = False
                    f_btime = time.time()
                # 发送BS
                pred_bs = self.get_bs_dict(weight)
                yield {"role": role, "content": msg_txt, "bs": pred_bs}
                sleep_time = self.speed_play * f_num - (time.time() - f_btime)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                if self.stop:  # 在生成当前bs序列时获取到新的提问时，打断动画
                    logger.info("准备中断当前对话...")
                    break

            # 动作复位
            for i in range(self.ending_duration):
                # 发送BS
                f_num += 1
                yield {"role": role, "content": msg_txt, "bs": zero_bs_dict}
                sleep_time = self.speed_play * f_num - (time.time() - f_btime)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as err:
            logger.error(f"Sound animation type error: {err}")
        self.standby_start_time = time.time()
        # return {'res': bs_weight}

    def play_audio(self):
        """
        播放音频
        Returns:

        """

        def split_list(lst, size):
            """
            将列表分割成指定大小的若干份
            Args:
                lst: 要分割的列表
                size: 每份的大小

            Returns: 分割后的列表

            """
            return [lst[i:i + size] for i in range(0, len(lst), size)]

        chunk_size = 1024
        while True:
            logger.info("============new turn============")
            with self.lock:
                logger.info("BS进入准备播放状态...")
                self.event_bs_play.set()

            logger.info("音频等待开始播放...")
            self.wav_stream = self.q_tts_wav.get()  # 阻塞get
            logger.info("音频开始播放。")
            time.sleep(self.waiting_error)
            for wav_chunck in split_list(self.wav_stream, chunk_size):  # 已修改，避免多次判断，计算，循环
                if not self.stop:
                    if self.stream.is_stopped():
                        self.stream.start_stream()
                    try:
                        self.stream.write(wav_chunck)
                        self.audio_play_time = time.time()
                    except Exception as e:
                        logger.error(e)
                        self.stream = self.p.open(
                            format=self.p.get_format_from_width(2),
                            channels=1,
                            rate=24000,
                            output=True)
                        continue
                else:
                    self.stream.stop_stream()
                    self.q_tts_wav.queue.clear()
                    break
            self.audio_play_time = time.time()

    def get_file_list(self, dir):
        '''
        获取目录下所有文件
        Args:
            dir: 目标目录

        Returns:
            file_list: 文件名列表

        '''
        file_list = []
        for root, dirs, files in os.walk(dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append(file_path)
        return file_list

    def gen_standby_anim(self):
        '''
        生成待机动画
        Returns:

        '''
        f_btime = time.time()
        zero_bs_dict = self.get_bs_dict(np.zeros((37,), dtype=np.float32))
        if f_btime - self.standby_start_time < self.standby_duration or \
                self.stop:  # 没超过等待时长，不播放待机动画; 获取到新问题时停止迭代，进入音频驱动循环
            time.sleep(0.01)
            return []
        f_num = 1
        standby_file = choice(self.standby_list)  # 随机一个待机动画序列
        seq_df = pd.read_hdf(standby_file, "data", dtype=np.float64)
        for index, row in seq_df.iterrows():
            # 获取到音频时停止迭代，进入音频驱动循环
            if self.stop:
                logger.info("中断当前待机动画。")
                for i in range(self.ending_duration):  # 表情复位
                    # 发送BS
                    f_num += 1
                    yield {"bs": zero_bs_dict}
                    sleep_time = self.speed_play * f_num - (time.time() - f_btime)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                break
            bs_dict = row.to_dict()
            yield {"bs": bs_dict}
            # sleep时间保证动画音频同步
            sleep_time = self.speed_play * f_num - (time.time() - f_btime)
            if sleep_time > 0:
                time.sleep(sleep_time)
            f_num += 1

    def gen_assign_anim(self, anim_file):
        """
        生成指定动画（如哭、笑、做鬼脸)
        Args:
            anim_file:

        Returns:

        """
        # 获取到新问题时停止迭代，进入音频驱动循环
        self.stop = False
        zero_bs_dict = self.get_bs_dict(np.zeros((37,), dtype=np.float32))
        if anim_file == '':
            time.sleep(0.01)
            return []
        f_btime = time.time()
        f_num = 1
        seq_df = pd.read_hdf(anim_file, "data", dtype=np.float64)
        for index, row in seq_df.iterrows():
            # 获取到音频时停止迭代，进入音频驱动循环
            if self.stop:
                logger.info("中断指定表情动画。")
                for i in range(self.ending_duration):  # 表情复位
                    # 发送BS
                    f_num += 1
                    yield zero_bs_dict
                    sleep_time = self.speed_play * f_num - (time.time() - f_btime)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                break
            bs_dict = row.to_dict()
            yield bs_dict
            # sleep时间保证动画音频同步
            sleep_time = self.speed_play * f_num - (time.time() - f_btime)
            if sleep_time > 0:
                time.sleep(sleep_time)
            f_num += 1

    def get_bs_dict(self, bs):
        """
        将bs数据转为字典格式
        Args:
            bs: 输出，numpy array类型

        Returns:

        """
        bs = bs.astype(float)
        bs_dict = dict()
        for idx, name in enumerate(FaceBlendShape):
            if name.name in MAPPING.keys():
                bs_dict[name.name] = max(bs[MAPPING[name.name]])
            else:
                bs_dict[name.name] = 0.0
        # 添加眼睛和头部姿态
        data, self.seq_data = self.seq_data[0, :], self.seq_data[1:]
        for bs_name, bs_value in zip(self._seq_name_speech, data):
            bs_dict[bs_name] = bs_value
        self.seq_data = np.append(self.seq_data, [data], axis=0)

        return bs_dict

    def __del__(self):
        # 插件销毁
        print("PluginsTemplate closed!")


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDFGAudioFace
