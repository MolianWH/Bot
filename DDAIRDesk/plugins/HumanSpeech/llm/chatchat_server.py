# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : chatchat_server.py
@Author     : MJJ
@Version    :
@Date       : 11/1/2023 11:09 AM 
@Description: Langchain-chatchat
@Update     :
@Software   : PyCharm
"""
import json
from loguru import logger
from .base import DDBaseLLM
from copy import deepcopy


class DDChatChat(DDBaseLLM):
    def __init__(self, config):
        super().__init__(config)
        self.url = f"{self.config['api_base_url']}/chat/knowledge_base_chat"
        self.headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        self.data = {
            "query": '',
            "knowledge_base_name": self.config['knowledge_base_id'],
            "top_k": self.config['top_k'],
            "score_threshold": self.config.get("score_threshold", 0.5),
            "history": [],
            "stream": True,
            "model_name": self.config.get("model", "openai-api"),
            "temperature": self.config['temperature'],
            "max_tokens": 0,
            "prompt_name": self.config.get("prompt_name", "default")
        }

    def _reset_data(self, question):
        # 设置查询的问题
        self.data['query'] = question

        if len(self.data["history"]) // 2 > self.max_history_turn:
            self.data["history"].pop(0)
        return self.data

    def _process_response(self, response):
        self.event_stop.clear()
        complete_ans = ''
        done = False
        try:
            for line in response.iter_content(None, decode_unicode=True):
                data = json.loads(line)
                if "answer" in data:
                    complete_ans += data["answer"]
                    yield data["answer"]
                if self.event_stop.is_set():
                    break
                if "docs" in data:  # 表示完整对话结束，后面是知识库出处信息
                    done = True
        except Exception as e:
            logger.error(f"Chat服务连接失败.{e}")

        # 存储历史对话
        if done and self.max_history_turn > 0:
            self.add_history(role='user', content=self.data['query'])
            self.add_history(role='assistant', content=complete_ans)
        response.close()

    def add_history(self, role: str = 'assistant', content: str = ''):
        """
        开放给用户的可调用的添加历史信息
        Args:
            role: 角色名，只能是['user', 'assistant']二选一
            content: 内容

        Returns:

        """
        if len(self.data["history"]) // 2 > self.max_history_turn:
            self.data["history"].pop(0)
        self.data["history"].append({"role": role,
                                     "content": content
                                     })

    def clear_history(self):
        self.data["history"] = []
