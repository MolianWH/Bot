# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : openai_server.py
@Author     : MJJ
@Version    :
@Date       : 11/1/2023 11:40 AM 
@Description: OpenAI ChatGPT服务
@Update     :
@Software   : PyCharm
"""
from loguru import logger
import openai
from .base import DDBaseLLM


class DDOpenAI(DDBaseLLM):
    def __init__(self, config):
        super().__init__(config)
        openai.api_key = self.config['api_key']
        openai.api_base = self.config["url"]
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
        self._reset_data(question)
        try:
            response = openai.ChatCompletion.create(
                model=self.config['model'],
                messages=[self.data, ],
                stream=True,
            )
            return self._process_response(response)
        except Exception as err:
            logger.error(f'OpenAI API 异常: {err}')
            return None

    def _reset_data(self, question):
        self.data['content'] = question

    def _process_response(self, response):
        self.event_stop.clear()
        try:
            for event in response:
                if event['choices'][0]['finish_reason'] == 'stop':
                    break
                delta = event['choices'][0]['delta']['content']
                yield delta
                if self.event_stop.is_set():
                    break
        except Exception as err:
            logger.error(f'OpenAI API 异常: {err}')
