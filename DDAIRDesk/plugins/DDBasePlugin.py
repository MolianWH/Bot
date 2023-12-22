# -*- coding: utf-8 -*-
# @Copyright © 2022 DreamDeck. All rights reserved. 
# @FileName   : DDBasePlugin.py
# @Author     : yaowei
# @Version    : 0.0.1
# @Date       : 2022/11/10 14:15
# @Description: write some description here
# @Update    :
# @Software   : PyCharm
import json
import os.path

import requests
from loguru import logger

from DDAIRDesk.tools.date_tool import datetime_verify
from DDAIRDesk.tools.dd_exception import PluginLoadFailException
from DDAIRDesk.tools.device_info_loader import DeviceInfoLoader
from DDAIRDesk.tools.read_yaml import read_yaml_all
from DDAIRDesk.tools.rsa_tool import str_decrypt, str2bin_encode, bin2str_decode

LICENSE_PATH = '../plugins/DDLICENSE'
DEVICE_CONF = '../config/.device_conf.yaml'


class DDBasePlugin:
    '''
    插件基类
    '''
    DDPluginDataFlow = {}
    device_info_loader = DeviceInfoLoader()
    _device_info = device_info_loader.device_info
    activated = False

    def __init__(self):
        logger.info('初始化DDBasePlugin...')
        self._check_file_exists_and_valid()
        self._activated = self._get_device_info()
        if not self._activated:  # 无本地存储文件
            self._activated = self._activate_device()

    def _get_device_info(self):  # 获取设备信息的同时执行快速检查
        logger.info('获取硬件信息中...')

        if os.path.exists(LICENSE_PATH):  # 存在设备信息文件quick check
            logger.info('已缓存鉴权信息,进行检验...')
            return self._quick_check()

    def _quick_check(self):
        with open(LICENSE_PATH, 'rb') as f:
            license_data = f.readlines()
            if license_data and license_data[0]:
                activate_infos = str(license_data[0], encoding='gbk')
                if activate_infos:  # 存在已保存信息
                    license_data = bin2str_decode(activate_infos).split('|')
                    # 方便临时调试
                    return True
                    if DDBasePlugin._device_info == str_decrypt(license_data[1]) + str_decrypt(
                            license_data[2]):  # 硬件信息一致
                        logger.info('硬件信息校验成功...')
                        valid_list = [self._device_id == str_decrypt(license_data[0]).split('|')[2],
                                      self._api_key == license_data[0],
                                      datetime_verify(str_decrypt(license_data[4])),
                                      datetime_verify(str_decrypt(license_data[5]))]
                        if not all(valid_list):  # 缓存的key与配置文件中的key不同,或其他信息不合法
                            logger.error('验证文件信息不完整')
                            raise PluginLoadFailException('插件加载异常')
                            # sys.exit()
                            # 存在key文件
                        logger.info('ApiKey一致性校验成功...')
                        return True
                return False
            else:
                logger.error('DDLICENSE文件异常')
                raise PluginLoadFailException('插件加载异常')
                # sys.exit()

    def _check_file_exists_and_valid(self):
        '''
        1.检查DDAPIKEY.yaml是否存在,不存在直接打印日志并退出;
        2.如果存在,检查内容是否合法;
        Returns:

        '''
        if not os.path.exists(DEVICE_CONF):  # 1
            logger.error('config/DDAPIKEY.yaml 配置目录下未找到激活配置文件')
            raise PluginLoadFailException('插件加载异常')
            # sys.exit()
        logger.info('检查Apikey文件...')
        dd_api_key = read_yaml_all(DEVICE_CONF)  # 存在激活配置文件
        try:
            self._api_key = dd_api_key['api_key']
            device_id = dd_api_key['device_id']
            validate_data = str_decrypt(self._api_key)
            if validate_data:
                self._device_id = validate_data.split('|')[2]
                logger.info('有效的Apikey...')
                if device_id != self._device_id:
                    logger.error('激活失败,device_id不一致')
                    raise PluginLoadFailException('激活失败,device_id不一致')
            else:
                logger.error('激活失败,无效的key')
                raise PluginLoadFailException('插件加载异常')
                # sys.exit()
        except KeyError as ke:
            logger.error('激活配置文件参数不合法')  # 2
            raise PluginLoadFailException('插件加载异常', ke)
            # sys.exit()
        except Exception as e:
            logger.error('激活失败:{}'.format(e))
            raise PluginLoadFailException('插件加载异常')
            # sys.exit()

    def _activate_device(self):  # 配置合法,不存在已缓存文件,执行请求服务
        logger.info('未发现缓存鉴权信息,请求后端服务进行校验...')
        header = {'content-type': 'application/json'}
        device_activate = {'apiKey': self._api_key, 'deviceId': self._device_id,
                           'deviceInfo': DDBasePlugin._device_info}
        json_text = json.dumps(device_activate)
        response = requests.post('https://test.dreeck.com:11443/cloudConfig/authentication/activateDevice',
                                 data=json_text, headers=header)
        try:
            if response.json()['data']:
                activate_infos = response.json()['data'].split('|')
                saved_data = response.json()['data']
                with open(LICENSE_PATH, 'wb') as dlk:
                    logger.info('激活成功,写入鉴权信息...')
                    dlk.write(bytes(str2bin_encode(saved_data), encoding='gbk'))
                    return True
            else:
                logger.error('激活失败,错误原因:{}'.format(response.json()['msg']))
                raise PluginLoadFailException('插件加载异常')
                # sys.exit()
        except Exception as e:
            logger.error('激活失败,错误原因:{} {}'.format(e, response.json()['msg']))
            raise PluginLoadFailException('插件加载异常')
            # sys.exit()

    def add_plugin_data(self, key, value):
        self.DDPluginDataFlow[key] = value

    def is_activated(self):
        return self._activated
