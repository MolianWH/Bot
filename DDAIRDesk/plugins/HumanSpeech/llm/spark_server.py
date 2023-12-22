# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : spark_server.py
@Author     : MJJ
@Version    :
@Date       : 11/1/2023 11:38 AM 
@Description: 星火API
@Update     :
@Software   : PyCharm
"""
import json
from time import mktime
from datetime import datetime
import base64
import datetime
import hashlib
import hmac
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from websocket import create_connection, WebSocketException
from urllib.parse import urlparse
from loguru import logger

from .base import DDBaseLLM


class DDSpark(DDBaseLLM):
    def __init__(self, config):
        super().__init__(config)
        self.url = self.create_url()
        self.data = {
            "header": {
                "app_id": self.config['appid'],
                "uid": "1234"
            },
            "parameter": {
                "chat": {
                    "domain": self.config['domain'],
                    "temperature": self.config['temperature'],
                    "max_tokens": self.config['max_tokens'],
                    # "top_k": self._top_p
                }
            },
            "payload": {
                "message": {
                    # 如果想获取结合上下文的回答，需要开发者每次将历史问答信息一起传给服务端，如下示例
                    # 注意：text里面的所有content内容加一起的tokens需要控制在8192以内，开发者如有较长对话需求，需要适当裁剪历史信息
                    "text": [
                        {"role": "user",
                         "content": ""}  # 用户的历史问题
                    ]
                }
            }
        }

    def query(self, question):
        """
        流式访问
        Args:
            question: 修改了prompt的问题

        Returns:

        """
        self._reset_data(question)
        ws = None
        try:
            ws = create_connection(self.url)
            # 返回查询的结果
            ws.send(json.dumps(self.data))
            return self._process_response(ws)
        except WebSocketException as e:
            logger.error("WebSocket请求异常", e)
            return None
        except Exception as e:
            logger.error("未知异常", e)
            return None
        finally:
            if ws:
                ws.close()

    def _reset_data(self, question):
        # 设置查询的问题
        self.data["payload"]["message"]["text"][0]["content"] = question

    def _process_response(self, ws):
        self.event_stop.clear()
        while True:
            response = json.loads(ws.recv())
            code = response['header']['code']
            if code != 0:
                print(f'请求错误: {code}, {response}')
                ws.close()
                break
            else:
                choices = response["payload"]["choices"]
                status = choices["status"]
                content = choices["text"][0]["content"]
                yield content
                if status == 2:
                    ws.close()
                    break
            if self.event_stop.is_set():
                break

    def create_url(self):
        host = urlparse(self.config['Spark_url']).netloc
        path = urlparse(self.config['Spark_url']).path
        api_secret = self.config['api_secret'].encode('utf-8')
        api_key = self.config['api_key']
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + path + " HTTP/1.1"

        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(api_secret, signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": host
        }
        # 拼接鉴权参数，生成url
        url = self.config['Spark_url'] + '?' + urlencode(v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        return url
