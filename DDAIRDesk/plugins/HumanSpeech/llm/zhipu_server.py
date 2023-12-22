# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : zhipu_server.py
@Author     : MJJ
@Version    :
@Date       : 11/1/2023 11:34 AM 
@Description: 
@Update     :
@Software   : PyCharm
"""

import json
from loguru import logger
import zhipuai
from .base import DDBaseLLM


class DDZhipu(DDBaseLLM):
    def __init__(self, config):
        super().__init__(config)
        zhipuai.api_key = self.config["api_key"]
        self.data = {
            "role": "user",
            "content": ""
        }

    def query(self, question):
        """
        流式访问
        Args:
            question: 修改了prompt的问题

        Returns:

        """
        # 设置查询的问题
        self.data['content'] = question
        # 返回查询的结果
        try:
            response = zhipuai.model_api.sse_invoke(
                model=self.config['model'],
                prompt=self.data,
                top_p=self.config['top_p'],
                temperature=self.config['temperature'],
            )
            return self._process_response(response)
        except Exception as e:
            logger.error("请求失败: %s", e)
            return None

    def _reset_data(self, question):
        # 设置查询的问题
        self.data['content'] = question

    def _process_response(self, response):
        self.event_stop.clear()
        for event in response.events():
            if event.event == "add":
                # print(event.data,end="", flush=True)
                yield event.data
            elif event.event == "error" or event.event == "interrupted":
                print(event.data)
            elif event.event == "finish":
                print(event.data)
                print(event.meta)
            else:
                print(event.data)
            if self.event_stop.is_set():
                break
