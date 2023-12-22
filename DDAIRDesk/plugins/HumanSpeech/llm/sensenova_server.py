# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : sense_server.py
@Author     : MJJ
@Version    :
@Date       : 11/1/2023 11:38 AM 
@Description: 商汤日日新
@Update     :
@Software   : PyCharm
"""
import json
from loguru import logger
from .base import DDBaseLLM
from copy import deepcopy


class DDSensenova(DDBaseLLM):
    def __init__(self, config):
        super().__init__(config)
        self.url = self.config["url"]
        self.headers = {
            'Content-Type': "application/json",
            'Authorization': self.config["api_key"]
        }
        self.data = {
            "model": self.config['model'],
            "messages": [],
            "temperature": self.config['temperature'],
            "top_p": self.config['top_p'],
            "max_new_tokens": self.config['max_new_tokens'],
            "repetition_penalty": 1,
            "stream": True,
            "user": "bot_test"  # "scg_test"
        }

    def _reset_data(self, question):
        # 设置查询的问题
        if len(self.data["messages"]) // 2 > self.max_history_turn:
            self.data["messages"].pop(0)

        self.data["messages"].append({"role": "user",
                                      "content": question})
        return self.data

    def _process_response(self, response):
        self.event_stop.clear()
        complete_ans = ''
        done = False
        try:
            for data in response.iter_content(chunk_size=None):
                string_data = data.decode('utf-8', 'ignore')
                data_lines = string_data.strip().split('\n\n')
                for line in data_lines:
                    if line != "data:[DONE]" and line.startswith('data:'):
                        json_data = json.loads(line[len('data:'):])
                        delta = json_data['data']['choices'][0]['delta']
                        complete_ans += delta
                        yield delta
                        if json_data["data"]["choices"][0]["finish_reason"] == "length":
                            logger.warning("max_new_tokens可能有点小")
                        if self.event_stop.is_set():
                            break
                    elif line == "data:[DONE]":
                        logger.info("Sensenova服务已完成")
                        done = True
                if self.event_stop.is_set():
                    break
        except Exception as e:
            logger.error(f"Sensenova服务异常。{e}")

        # 存储历史对话
        if done and self.max_history_turn > 0:
            self.add_history('assistant', complete_ans)
        else:
            self.data["messages"].pop(-1)  # 不是完整对话，删除最后一个问题
        response.close()

    def add_history(self, role: str = 'assistant', content: str = ''):
        """
        开放给用户的可调用的添加历史信息
        Args:
            role: 角色名，只能是['user', 'assistant']二选一
            content: 内容

        Returns:

        """
        if len(self.data["messages"]) // 2 > self.max_history_turn:
            self.data["messages"].pop(0)
        self.data["messages"].append({"role": role,
                                      "content": content
                                      })

    def clear_history(self):
        self.data["messages"] = []
