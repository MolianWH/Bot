# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : base.py
@Author     : MJJ
@Version    :
@Date       : 11/1/2023 11:07 AM 
@Description: LLM基类
@Update     :
@Software   : PyCharm
"""
import threading
import requests
from loguru import logger
import json
import time


class DDBaseLLM:
    def __init__(self, config):
        self.config = config
        self.url = ''
        self.data = {}
        self.headers = ''
        self.event_stop = threading.Event()
        self.max_request_attempts = self.config.get('max_request_attempts', 2)
        self.max_history_turn = self.config.get('max_history_turn', 0)  # 最大历史对话轮数，0表示部存历史对话

    def query(self, question, knowledge_base_id=''):
        """
        流式访问
        Args:
            question: 修改了prompt的问题
            knowledge_base_id: 知识库ID

        Returns:

        """
        data = self._reset_data(question)

        if "knowledge_base_name" in data and knowledge_base_id:
            data["knowledge_base_name"] = knowledge_base_id

        for attempt in range(self.max_request_attempts):
            try:
                response = requests.post(self.url,
                                         stream=True,
                                         headers=self.headers,
                                         json=data,
                                         timeout=5)
                response.raise_for_status()  # 检查HTTP响应状态
                return self._process_response(response)
            except requests.Timeout:
                logger.warning("请求超时")
            except requests.RequestException as e:
                logger.error("网络请求失败:{}".format(e))
            except json.JSONDecodeError as e:
                logger.error("JSON解析失败:{}".format(e))
            logger.warning(f"尝试重新请求中, 当前请求次数/最大请求次数:{attempt + 1}/{self.max_request_attempts}")
            time.sleep(1)
        return None

    def add_history(self, role: str = 'assistant', content: str = ''):
        """
        开放给用户的可调用的添加历史信息
        Args:
            role: 角色名，只能是['user', 'assistant']二选一
            content: 内容

        Returns:

        """
        pass

    def clear_history(self):
        """
        清空历史信息
        Returns:

        """
        pass

    def _reset_data(self, question):
        raise NotImplementedError("This method needs to be implemented by the subclass.")

    def _process_response(self, response):
        raise NotImplementedError("This method needs to be implemented by the subclass.")

    def stop(self):
        self.event_stop.set()

    def __call__(self, in_data, knowledge_base_id=''):
        return self.query(in_data, knowledge_base_id)
