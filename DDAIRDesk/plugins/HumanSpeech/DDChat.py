# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : DDChat-1.0.py.py
@Author     : MJJ
@Version    :
@Date       : 10/13/2023 3:19 PM
@Description: 对应langchain-chatchat，chatglm2-6b
@Update     :
@Software   : PyCharm
"""

import sys
import threading
from loguru import logger
import importlib

from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from DDAIRDesk.tools.read_yaml import read_yaml
from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin


class DDChat(DDBasePlugin):
    def __init__(self, yaml_path):
        super(DDChat, self).__init__()
        try:
            self.config = read_yaml(yaml_path, 'DDChat')
            self._prompt = self.config['prompt']
            self.model_name = self.config['model_name']
            self.model_cfg = self.config[self.model_name]

        except FileNotFoundError as e:
            print(f"配置文件{yaml_path}不存在：{e}")
            exit()
        except KeyError as e:
            print(f"配置文件{yaml_path}中{self.__class__.__name__}出错!{e}")
            exit()

        self.stop = True
        self.event_over = threading.Event()
        self.llm = self._load_llm()

    def _load_llm(self):
        try:
            module = importlib.import_module(f"DDAIRDesk.plugins.HumanSpeech.llm.{self.model_name.lower()}_server")
            service_class = getattr(module, f"DD{self.model_name}")
            return service_class(self.model_cfg)
        except ImportError:
            print(f"无法导入{self.model_name}模块")
            exit()
        except AttributeError:
            print(f"DD{self.model_name}类不存在")
            exit()

    def __call__(self, in_data, knowledge_base_id=''):
        """
        chatGLM LangChain txt to txt, question to answer
        Args:
            in_data: 用户输入问题
            knowledge_base_id: 知识库ID

        Returns: 迭代器，回答的每一句，以标点符号分割。
                如果打断发生，则返回至打断的位置的回答。
        """
        logger.info("进入Chat环节...")
        self.event_over.clear()
        logger.info("Chat修改over状态...")
        self.stop = False
        msg = ""

        in_data = self._prompt.format(question=in_data)
        resp = self.llm(in_data, knowledge_base_id)
        if resp is None:
            yield "我刚刚在网络的世界里走丢了，再问我一个问题试试看吧。"
            yield "<Finish>"
            return
        for delta in resp:
            msg += delta
            if delta[-1:] in '。?？!！;；,，:：\n':
                if msg not in ["\\n", "\n"]:
                    yield msg
                msg = ''
            if self.stop:
                self.llm.stop()
                return
        yield "<Finish>"

    def add_history(self, role: str = 'assistant', content: str = ''):
        if role not in ['user', 'assistant']:
            raise ValueError("role must be 'user' or 'assistant'")
        self.llm.add_history(role, content)

    def clear_history(self):
        self.llm.add_history()

    def __del__(self):
        print()
        print("DDHumanSpeech closed!")


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDChat
