# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : demo.py
# @Author     : HYD
# @Version    :
# @Date       : 2023/5/11 18:27
# @Description: LangChain对话机器人
# @Update     :
#              2023/8/8 1. 待机文本为空时不发UE；2. 线程设置daemon=True; 3. 解决语音打断后还要再生成一段BS动画BUG
#              2023/7/31 删除冗余变量和注释
# @Software   : PyCharm

import re
import string
from zhon.hanzi import punctuation
import os.path
import threading
import time
from threading import Thread
from queue import Queue
from random import choice, random

import redis
from loguru import logger
import cv2
from xpinyin import Pinyin
from pylivelinkface import PyLiveLinkFace, FaceBlendShape
import matplotlib.path as mpltPath

from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin
from DDAIRDesk.plugins.Communication.DDSocket import DDSocket
from DDAIRDesk.tools.read_yaml import read_yaml
from DDAIRDesk.tools.ddio import print_colored, print_interval, DDFont, wait_interval
from DDAIRDesk.tools.utils import *
from DDAIRDesk.plugins.PluginLoader import PluginLoaderMini


class DDChatBot(DDBasePlugin):
    """
        聊天机器人管线，完成了以下工作：
        1. ASR：语音识别，实现语音转文字
        2. ChatGLM对话
        3. TTS：语音合成，实现文字转音频
        4. AudioFace: 实现音频转动画bs
        5. 聊天打断功能
        6. 待机动画功能
    """

    def __init__(self, yaml_path):
        super(DDChatBot, self).__init__()
        global STANDBY_INTERVAL

        try:
            self.config = read_yaml(yaml_path, 'DDChatBot')
            # ======通信配置======
            self.tcp_server_info = self.config['tcp_server']
            self.livelink_info = self.config["livelink"]  # 通信接口
            # ======文本配置=========
            self.sensitive = read_yaml(self.config['sensitive'], 'sensitive')  # 敏感词
            self.fuzziness = read_yaml(self.config['fuzziness'], 'fuzziness')  # 模糊词
            self.standby_chat = read_yaml(self.config['standby_text'], 'standby_chat')  # 待机语音
            self.bye_text = self.config['bye_text']  # 再见
            self.wake_words = self.config["wake_words"]  # 唤醒词
            self.greet_face_wake_up = self.config['greet_face_wake_up']  # 人脸唤醒问候语
            self.greet_audio_wake_up = self.config['greet_audio_wake_up']  # 语音唤醒问候语
            self.greet_guide = self.config['greet_guide']  # 引导交互
            # ======时间阈值========
            self.close_interaction_time = self.config['close_interaction_time']  # 超过此值关闭交互流程
            self.standby_interval = self.config['standby_audio_interval']  # 待机语音间隔
            self.greets_interval_time = self.config['greets_interval_time']  # 识别到人脸后多久没交互，开始介绍公司
            self.gaze_frame_threshold = self.config['gaze_frame_threshold']  # 人在区域内多久打招呼
            self.region = [tuple(element) for element in self.config['region']]
            self.region_path = mpltPath.Path(self.region)
            # ======cache==========
            self.cache_cfg = DotDict(self.config.get("cache", {}))

        except FileNotFoundError as e:
            logger.error(f"配置文件{yaml_path}不存在：{e}")
            exit()
        except KeyError as e:
            logger.error(f"配置文件{yaml_path}中{self.__class__.__name__}出错!{e}")
            exit()

        # 多进程队列通信用mp.Queue; 多线程通信用python自带的queue
        self.q_asr_txt = Queue(maxsize=1)  # 存放语音识别的文字
        self.q_chat_txt = Queue(maxsize=100)  # 存放chat输出文字
        self.q_tts_wav = Queue(maxsize=100)  # 存放tts合成的语音文件
        self.q_audio_face = Queue(maxsize=1)  # 用于扩展虚拟人
        self.livelink_data = PyLiveLinkFace(name=self.livelink_info["name"],
                                            fps=self.livelink_info["fps"],
                                            filter_size=self.livelink_info["filter_size"])
        self.pinyin = Pinyin()
        self.event_play = threading.Event()
        self.event_standby_switch = threading.Event()
        self.event_start_interaction = threading.Event()
        self.bots_chat_stop = True
        self.last_speech_time = 0
        self.last_valid_face_time = time.time()
        self.default_role = "BotA"
        self.has_greet = False  # 是否是刚打完招呼
        if self.cache_cfg.use_cache:
            # self._cache = diskcache.Cache(self.cache_path)
            self._cache = redis.Redis(host=self.cache_cfg.host,
                                      password=self.cache_cfg.password,
                                      port=self.cache_cfg.port,
                                      db=self.cache_cfg.db)  # 改为配置

        # 注册插件
        local_yaml_path = "../config/local/DDAudioFacePluginsConf.yaml"
        self.plugins_loader = PluginLoaderMini(local_yaml_path)
        plugins_dict = self.plugins_loader.get_plugins()

        self.DDSound = plugins_dict['DDSound']
        self.DDCamera = plugins_dict['DDCamera']
        self.DDSpeech = plugins_dict["DDSpeech"]  # ASR
        self.DDChat = plugins_dict['DDChat']
        self.DDTTS_BotA = plugins_dict['DDTTS']
        self.DDFGAudioFace = plugins_dict['DDFGAudioFace']
        self.DDFaceRecognition = plugins_dict['DDFaceRecognition']
        self.DDHumanPose = plugins_dict['DDHumanPose']

        # chat对话内容通过TCP服务发给UE
        self.dd_socket = DDSocket()
        self.event_play.set()
        self.event_standby_switch.set()

        self.event_bs_play = threading.Event()
        self.event_bs_play.clear()

    def load_model(self):
        """模型加载"""
        self.q_chat_txt.put({"role": self.default_role,
                             "asr": "power_on",
                             "content": "智能助手小D已连接！"})  # 开机语音
        self.q_chat_txt.put({"role": self.default_role,
                             "asr": "power_on",
                             "content": "<Finish>"})
        # 模型加载
        self.DDSpeech.load_model()
        self.DDFGAudioFace.load_model()
        self.DDFaceRecognition.load_model()

        # 初始化通信
        self._init_communication()

        # 创建线程
        thread_pool = []
        thread_pool.append(Thread(target=self.task_asr))
        thread_pool.append(Thread(target=self.task_audio_face))
        thread_pool.append(Thread(target=self.task_chat))
        thread_pool.append(Thread(target=self.task_tts))
        # thread_pool.append(Thread(target=self.task_face_recognition))

        # 开启线程
        for task in thread_pool:
            task.daemon = True  # 守护线程
            task.start()
            # task.join()  # join阻塞主线程
        logger.info("模型加载完毕，准备就绪。")

    def _init_communication(self):
        '''初始化通信参数'''
        socket_type = self.dd_socket.socket_type
        self.dd_socket.set_sock(set_pairs=[
            {"sock_type": socket_type.TCP_SERVER, "addr": tuple(self.tcp_server_info["addr"]),
             "num": self.tcp_server_info["conn_num"]},
            {"sock_type": socket_type.UDP_CLIENT, "addr": tuple(self.livelink_info["addr"])}
        ])
        self.dd_socket.tcp_server.start_send_thread()
        self.dd_socket.tcp_server.start_heart_thread()
        self.dd_socket.tcp_server.start_recv_thread()
        self.dd_socket.udp_client.start_send_thread()
        print("socket init successful.")

    def rsa_filter(self, text):
        """判断是否是中文https://blog.csdn.net/sinat_29891353/article/details/129353893
        正常text里面是中文汉字+英文标点
        中文字符的编码范围为： u'\u4e00' -- u'\u9fff：只要在此范围内就可以判断为中文字符串
        Args:
            text:

        Returns:
        """
        # 如果含有非中文字符，不合法
        text = re.sub('[{}{}{}]'.format(string.punctuation, punctuation, ' '), "", text)
        # pattern = re.compile(r'[^\u4e00-\u9fa5]')
        # match = pattern.search(text)
        # 判断除去标定符号后是否为空
        if text == "":
            return None

        # 包含某些误识别关键词
        pattern = '|'.join(self.sensitive)
        # if match:
        #     return None
        if re.search(pattern, text) or len(text) == 1:
            return None
        else:
            return text

    def set_interrupt(self):
        btime_while = time.time()
        self.event_play.clear()

        self.DDChat.stop = True
        self.DDTTS_BotA.stop = True
        self.DDFGAudioFace.stop = True  # 用于打断待机动画
        self.bots_chat_stop = True  # 打断两个机器人聊天
        # 清空所有队列数据
        self.DDChat.event_over.wait()
        self.DDTTS_BotA.event_over.wait()
        self.q_asr_txt.queue.clear()
        self.q_chat_txt.queue.clear()
        self.q_tts_wav.queue.clear()  # 使用内置clear方法清空效率更高
        self.event_play.set()

        self.q_chat_txt.queue.clear()
        self.q_tts_wav.queue.clear()  # 使用内置clear方法清空效率更高

        logger.info("队列清理完成。")
        print("打断耗时:", time.time() - btime_while)

    def run_face_goodbye(self):
        """
        人脸离开区域时说再见
        Returns:

        """
        random_bye = choice(self.bye_text)
        self.q_chat_txt.put({"role": self.default_role,
                             "asr": "face_goodbye",
                             "content": random_bye})
        self.q_chat_txt.put({"role": self.default_role,
                             "asr": "face_goodbye",
                             "content": "<Finish>"})

    def run_introduce(self):
        """
        主动介绍公司、产品
        Returns:

        """
        logger.info("播放待机语音")
        self.bots_chat_stop = False
        random_key, random_chat = choice(list(self.standby_chat.items()))
        # random_chat = self.standby_chat["test"]
        for chat in random_chat:  # 一组对话
            role, text = chat.split("：")
            self.event_play.wait()
            self.q_chat_txt.put({"role": role,
                                 "asr": "introduce",
                                 "content": text})
            if self.bots_chat_stop:
                break
            time.sleep(0.5)
        self.q_chat_txt.put({"role": role,
                             "asr": "dd_introduce",
                             "content": "<Finish>"})

    def run_guide(self, name, group):
        """
        引导交互
        Returns:

        """
        if group == 'staff':
            content = "{}赶快去干活！".format(name)
        else:
            content = self.greet_guide.format(name)
        msg = {"role": self.default_role,
               "asr": "dd_guide",
               "content": content}
        self.set_interrupt()
        self.q_chat_txt.put(msg)
        self.q_chat_txt.put({"role": self.default_role,
                             "asr": "dd_guide",
                             "content": "<Finish>"})
        self.DDChat.clear_history()
        self.DDChat.add_history(role='assistant', content=content)

    def run_greet_face(self, name):
        """
        人脸唤醒后打招呼
        Args:
            name: 客户名

        Returns:

        """
        self.set_interrupt()
        content = self.greet_face_wake_up.format(name)
        pattern = '(?<=[{}{}{}])'.format(string.punctuation, punctuation, ' ')
        sentences = re.split(pattern, content)
        # 去除空白字符（例如空格）
        sentences = [sentence.strip() for sentence in sentences]
        sentences.append("<Finish>")
        for i, sentence in enumerate(sentences, 1):
            msg = {"role": self.default_role,
                   "asr": "greet_face",
                   "content": sentence}
            self.q_chat_txt.put(msg)
        self.DDChat.add_history(role='assistant', content=content)
        self.dd_socket.tcp_server.set_data(content.encode())
        self.has_greet = True

    def keywords_action(self, user_input):
        """
        关键词动作触发
        Args:
            user_input: 用户提问文本内容识别结果

        Returns:
            True: 是关键词，触发对应动作
            False: 不是关键词，不触发动作

        """
        user_input_pinyin = self.pinyin.get_pinyin(user_input, " ")
        txt = ''
        if user_input_pinyin in ["ke ji zhan shi"] or \
                "ke ji zhan shi" in user_input_pinyin:
            self.send_ue_chat({"role": "Jump", "content": "1"})  # 将页面跳转消息发送给UE
            txt = "已为您切换到科技展示，请看大屏。"
            print("科技展示")
        elif user_input_pinyin in ["mang he shou mai"] or \
                "mang he" in user_input_pinyin:
            self.send_ue_chat({"role": "Jump", "content": "2"})  # 将页面跳转消息发送给UE
            txt = "已为您切换到盲盒售卖，请看大屏。"
            print("盲盒售卖")
        elif user_input_pinyin in ["huan jing gan zhi"] or "天气" in user_input or \
                "huan jing gan zhi" in user_input_pinyin:
            self.send_ue_chat({"role": "Jump", "content": "3"})  # 将页面跳转消息发送给UE
            txt = "已为您切换到环境感知，请看大屏。"
            print("环境感知")
        elif user_input_pinyin in ["gao xiao xin wen"] or \
                "gao xiao xin wen" in user_input_pinyin:
            self.send_ue_chat({"role": "Jump", "content": "4"})  # 将页面跳转消息发送给UE
            txt = "已为您切换到高校新闻，请看大屏。"
            print("高校新闻")
        elif user_input_pinyin in ["fan hui zhu ye", "fan hui shou ye"] or \
                (len(user_input) < 10 and "返回" in user_input):
            self.send_ue_chat({"role": "Jump", "content": "5"})  # 将页面跳转消息发送给UE
            txt = "已返回主页。"
            print("返回主页")
        else:
            pass
        return txt

    def wake_up(self, user_input):
        """
        唤醒词唤醒
        Args:
            user_input:

        Returns:

        """
        wake_word = re.sub('[{}{}{}]'.format(string.punctuation, punctuation, ' '), "", user_input)
        if wake_word in self.wake_words:
            if wake_word == self.wake_words[0]:
                self.default_role = "BotA"
            self.send_ue_chat({"role": "User", "content": user_input})  # 将用户提问消息发送给UE
            return self.greet_audio_wake_up
        return ''

    def replace_homophones(self, text, replacement_dict):
        """
        模糊音替换
        """
        for i in range(len(text)):
            for num in [2, 3, 4]:
                words = text[i:i + num]
                pinyin = self.pinyin.get_pinyin(words, ' ')
                if pinyin in replacement_dict:
                    text = text.replace(words, replacement_dict[pinyin])
        return text

    def check_user_input(self, user_input):
        """
        模糊音矫正，唤醒，开启跳转界面
        Args:
            user_input:

        Returns:

        """
        # 模糊音矫正
        user_input = self.replace_homophones(user_input, self.fuzziness)
        print_colored("fuzziness output:" + user_input, DDFont.GREEN)
        # 唤醒词唤醒
        txt = self.wake_up(user_input)
        if txt != '':
            return {"label": "wake_up", "txt": txt}
        # # 关键词触发页面跳转
        # txt = self.keywords_action(user_input)
        # if txt != '':
        #     return {"label": "page_jump", "txt": txt}

        self.send_ue_chat({"role": "User", "content": user_input})
        txt = user_input
        return {"label": "q_asr", "txt": txt}

    def task_asr(self):
        """主流程调用。本线程内做了以下工作：
        1. 语音识别（whisper）
        2. whisper识别结果过滤
        3. whisper识别结果通过队列共享给其他线程
        Args:
            sound:

        Returns:

        """
        self.DDSound()
        for sound in self.DDSound:
            self.event_start_interaction.wait()
            output = self.DDSpeech(sound)
            if output and output['res']:
                rsa_final = self.rsa_filter(output['res'])
                if rsa_final is None:
                    content = "不合法语句: " + output['res']
                    print_colored(content, DDFont.RED)
                    self.set_interrupt()
                    # 打断之后再向队列放数据
                    self.q_chat_txt.put({"role": self.default_role,
                                         "asr": "sensitive_voc",
                                         "content": "为了维护友善和尊重的社交环境，请不要在问题中使用包含敏感词汇的内容。感谢您的合作和理解！"})
                    self.q_chat_txt.put({"role": self.default_role,
                                         "asr": "sensitive_voc",
                                         "content": "<Finish>"})
                else:
                    print_colored(f"asr_output:{output['res']}", DDFont.GREEN)
                    self.has_greet = False  # 已经识别到用户问题了，不必再5秒内介绍
                    res = self.check_user_input(output['res'])  # 先将结果发送UE，减少视觉延时

                    self.set_interrupt()
                    # 打断之后再向队列放数据
                    if res["label"] != "q_asr":
                        self.q_chat_txt.put({"role": self.default_role, "asr": res["label"], "content": res["txt"]})
                        self.q_chat_txt.put({"role": self.default_role, "asr": res["label"], "content": "<Finish>"})
                    else:
                        self.q_asr_txt.put({"role": "User", "content": res["txt"]})

    def task_chat(self):
        """
        chatGLM LangChain txt to txt, question to answer
        """
        while True:
            self.DDChat.event_over.set()
            self.event_play.wait()
            asr_input = self.q_asr_txt.get()
            asr_input = asr_input.get("content", "")
            self.last_speech_time = time.time()
            question_id = consistent_hash(asr_input)  # 生成问题的唯一ID，不随程序生命周期变化而变化，MD5
            b_time = time.time()
            # TODO: 对问题筛选
            # 配置文件配置”使用缓存“，随机缓存概率小于阈值，进入缓存搜索
            prob = random()
            if self.cache_cfg.use_cache and prob < self.cache_cfg.cache_prob:
                cached_data = self._cache.get(f"qa:{question_id}")  # 查询缓存
                # 问题已经存在缓存中
                if cached_data:
                    audio_key = f"audio_files_{self.DDTTS_BotA.voice}"   # 缓存中音频的键
                    data = json.loads(cached_data)
                    # chat和音频缓存中都有
                    if data.get(audio_key) is not None:
                        logger.info("使用缓存回复，更新缓存命中次数。")
                        data["hit_count"] += 1
                        self._cache.set(f"qa:{question_id}", json.dumps(data, ensure_ascii=False))  # 更新命中次数
                        # 获取chat和tts直接发给bs管线
                        for i in range(len(data[audio_key])):
                            with open(data[audio_key][i], 'rb') as file:
                                wav_stream = file.read()
                                self.q_tts_wav.put({"role": data['role'],
                                                    "content": data["answer"][i],
                                                    "wav_stream": wav_stream})
                        continue
                    else:  # 缓存中有chat内容，但是音频没有，需要重新生成音频
                        logger.info("使用缓存文本，重新生成音频。")
                        for i in range(len(data["answer"])):
                            self.q_chat_txt.put({"role": self.default_role,
                                                 "asr": asr_input,
                                                 "content": data["answer"][i]})

            # 生成新的回复
            logger.info(f"GLM准备回答(prob：{prob})：")
            chat_ans = self.DDChat(asr_input)
            for ans in chat_ans:
                ans = re.sub(r'{}|{}|{}|{}|{}|{}'.format('回答：', '回答:', '<幽默>', '小D：', '<自然>', '小D:'), "",
                             ans)
                logger.info("Chat: " + ans + "(T:{:.2f})".format(time.time() - b_time))
                # print(ans+"(T:{:.2f})".format(time.time()-b_time), end='')
                self.q_chat_txt.put({"role": self.default_role,
                                     "asr": asr_input,
                                     "content": ans})
                b_time = time.time()

    def task_tts(self):
        full_wav_list = []
        response_list = []
        while True:
            # 初始化
            time.sleep(0.01)
            self.DDTTS_BotA.event_over.set()
            self.event_play.wait()
            chat_info = self.q_chat_txt.get()
            self.last_speech_time = time.time()
            role = chat_info["role"]  # 角色名
            msg = chat_info["content"]  # 对话内容
            question = chat_info["asr"]
            question_id = consistent_hash(question)  # 对应的ASR
            btime_tts = time.time()

            if msg != '<Finish>':
                wav_dir = f"{self.cache_cfg.path}/{self.DDTTS_BotA.voice}"
                os.makedirs(wav_dir, exist_ok=True)
                filename = f"{wav_dir}/{consistent_hash(msg)}.wav"
                # 保存文件
                if not os.path.exists(filename):
                    # 推理
                    wav_stream = self.DDTTS_BotA(msg)
                    with open(filename, 'wb') as file:
                        file.write(wav_stream)
                # 使用缓存音频文件
                else:
                    with open(filename, 'rb') as file:
                        wav_stream = file.read()
                # 数据流传给bs
                if wav_stream != b'':
                    self.q_tts_wav.put({"role": role, "content": msg, "wav_stream": wav_stream})
                    print_colored(f"TTS:{msg}, Time:{(time.time() - btime_tts):.2f}", DDFont.BLUE)
                # 完整对话列表中添加分句
                full_wav_list.append(filename)
                response_list.append(msg)
            else:  # 完整对话结束，完整对话音频写缓存
                if self.is_write_cache(question, response_list):
                    cached_data = self._cache.get(f"qa:{question_id}")  # 查询缓存
                    # 缓存中没有问题。
                    if not cached_data:  # 写缓存

                        cache_data = {
                            "question": question,
                            "role": role,
                            "answer": response_list,
                            f"audio_files_{self.DDTTS_BotA.voice}": full_wav_list,  # 此时音频为空，留在TTS中缓存改写
                            "hit_count": 1  # 初始命中次数1
                        }
                        self._cache.set(f"qa:{question_id}", json.dumps(cache_data, ensure_ascii=False))
                        logger.info("缓存已写入")
                    # 之前缓存过，更新缓存
                    else:
                        data = json.loads(cached_data)
                        data["hit_count"] += 1
                        data["answer"] = response_list  # 有可能是问题不变，答案需要更新
                        data[f"audio_files_{self.DDTTS_BotA.voice}"] = full_wav_list
                        logger.info("缓存已更新")
                # 清空完整对话列表
                full_wav_list = []
                response_list = []

    def is_write_cache(self, question, response_list):
        """
        判断是否需要写缓存
        Returns:

        """
        if (question not in ['wake_up', 'greet_face', 'dd_guide', 'dd_introduce',
                             'face_goodbye', 'power_on',"sensitive_voc"]) and \
                self.cache_cfg.use_cache and \
                "我刚刚在网络的世界里走丢了，再问我一个问题试试看吧。" not in response_list:
            return True
        return False

    def task_audio_face(self):
        """
        wav to bs animation
        """
        while True:
            if self.q_tts_wav.qsize() > 0:  # 队列非空
                self.event_play.wait()
                tts_info = self.q_tts_wav.get()  # 阻塞
                self.last_speech_time = time.time()
                bs_info = self.DDFGAudioFace(tts_info)
                chat_info = {"role": tts_info.get("role", ''), "content": tts_info.get("content", '')}
                self.send_ue_chat(chat_info)  # 音频开始播放时才，将回答信息返回给UE用于显示。
            else:
                bs_info = self.DDFGAudioFace.gen_standby_anim()  # 4. 没有数据时生成待机动画
            for info in bs_info:  # bs数据实时发送
                role = info.get("role", '')
                bs = info.get("bs", '')
                self.send_ue_bs(bs, role)
            self.event_bs_play.set()

    def draw_region(self, image):
        """ 绘制多边形 """
        for i, point in enumerate(self.region):
            cv2.circle(image, point, 3, (0, 0, 255), -1, cv2.LINE_AA)
            if i > 0:
                cv2.line(image, self.region[i - 1], point, (0, 255, 0), 2, cv2.LINE_AA)
            if i == 3:
                cv2.line(image, self.region[3], self.region[0], (0, 255, 0), 2, cv2.LINE_AA)
        return image

    # def task_face_recognition(self):
    def __call__(self, *args, **kwargs):
        """人脸识别引导用户线程

        Returns:

        """
        self.event_bs_play.wait()
        logger.info("人脸识别唤醒线程开启")
        self.DDCamera()
        last_name = ''
        in_region_duration = 0
        last_in_region_status = False
        for frame in self.DDCamera:
            time.sleep(0.02)
            image = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            image = self.draw_region(image)

            if self.last_speech_time < self.DDFGAudioFace.audio_play_time:
                self.last_speech_time = self.DDFGAudioFace.audio_play_time  # 更新说话时间
            is_in_region = False
            res = self.DDHumanPose(image, True)
            poses, image = res['res'], res['out_img']
            res = self.DDFaceRecognition(image, True)
            faces, image = res['res'], res['out_img']
            name = ''
            group = ''
            # 找人
            for pose in poses:
                left_foot = pose[15]
                right_foot = pose[16]
                middle_foot = tuple(((left_foot + right_foot) // 2)[:2].tolist())
                # 判断脚的中点是否在多边形内
                inside = self.region_path.contains_point(middle_foot)
                if inside:
                    is_in_region = True
                    nose = tuple(pose[0][:2].tolist())
                    cv2.circle(image, nose, 3, (0, 0, 255), -1, cv2.LINE_AA)
                    # 查找人脸框
                    for face in faces:
                        box_corner = face['bbox']
                        box = [(max(box_corner[0], 0), max(box_corner[1], 0)),
                               (max(box_corner[2], 0), max(box_corner[1], 0)),
                               (max(box_corner[2], 0), max(box_corner[3], 0)),
                               (max(box_corner[0], 0), max(box_corner[3], 0))]
                        face_box_path = mpltPath.Path(box)
                        # 判断区域内的人是哪个人（区域内的人鼻子点在哪个人脸框中）
                        if face_box_path.contains_point(nose):
                            name = face['user_name']
                            group = face['group']
                            if name == last_name:
                                break  # 直至找到上一个交互的人还在区域内，停止迭代找人脸框
                    break  # 停止找人体框

            if is_in_region:  # 人在交互区域内：
                in_region_duration = (in_region_duration + 1) % 1024
                # 开启交互流程：当前交互流程在关闭状态，出现有效人脸
                self.last_valid_face_time = time.time()  # 记录最后一次有效人脸出现的时间
                if not self.event_start_interaction.is_set():
                    self.event_start_interaction.set()
                    logger.info(f"开启互动模式...")
                # 打招呼：换人了；人在区域内停留10帧；上一次有人出去过
                # logger.info(
                #     f"name:{name}, last_name:{last_name}, duration:{in_region_duration}, last_in:{last_in_region_status}")
                if name != last_name and \
                        in_region_duration > self.gaze_frame_threshold and \
                        not last_in_region_status:  # 打招呼
                    logger.info(f"{name}互动中...")
                    last_name = name
                    self.run_greet_face(name)
                    in_region_duration = 0
                    last_in_region_status = is_in_region
                # if name != last_name:
                #     last_name = name
            else:
                self.has_greet = False
                in_region_duration = 0
                last_in_region_status = is_in_region
                guide_name = faces[0]['user_name'] if len(faces) > 0 else ''
                guide_group = faces[0]['group'] if len(faces) > 0 else ''

                last_name = '无人'
                # 关闭交互流程：当前交互流程在开启状态，有效人脸消失的时间超过指定阈值
                if self.event_start_interaction.is_set() and (
                        time.time() - self.last_valid_face_time > self.close_interaction_time):
                    logger.info("长时间无有效人脸，进入人脸识别唤醒模式...")
                    self.event_start_interaction.clear()
                    # self.face_goodbye()
                # 引导交互：当前交互流程处于关闭状态，人都在区域外移动，且距离上次引导用户的时间超过设定的阈值
                if not self.event_start_interaction.is_set() and len(poses) > 0 and \
                        (time.time() - self.last_speech_time > self.standby_interval):
                    logger.info("检测到行人，引导交互！！")
                    self.set_interrupt()
                    self.run_guide(guide_name, guide_group)
                    self.last_speech_time = time.time()

            # 主动介绍
            now = time.time()
            interval = (now - self.last_speech_time)
            if self.has_greet and \
                    is_in_region and \
                    interval > self.greets_interval_time:
                logger.info("没有询问问题，主动介绍公司及产品")
                self.run_introduce()
                self.last_speech_time = time.time()
                self.has_greet = False

            cv2.imshow("debug", image)
            cv2.waitKey(1)

    def send_ue_chat(self, data_dict: dict = {"role": "", "content": ""}):
        """
        将对话内容发给UE
        Args:
            data_dict: 对话文本, 字典格式，role表示角色，content表示文本
        """
        json_data = json.dumps(data_dict, ensure_ascii=False)
        self.dd_socket.tcp_server.set_data(json_data.encode())  # 将用户提问消息发送给UE

    def send_ue_bs(self, face_bs, role):
        '''
        TCP服务器发送到UE
        Args:
            face_bs: 面捕blendshape
            livelink_data: PyLiveLinkFace对象
            udp_client:

        Returns:

        '''
        # 生成面捕blendshape数据
        for bs_name, bs_value in face_bs.items():  # 这里做滤波，编码等处理
            self.livelink_data.set_blendshape(FaceBlendShape[bs_name], bs_value)

        # 发送数据
        self.dd_socket.udp_client.set_data(self.livelink_data.encode())

    def shutdown_gracefully(self):
        """
        安全退出
        Returns:

        """
        self.plugins_loader.release_all_plugins()
