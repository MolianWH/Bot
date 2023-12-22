# @Copyright © 2022 DreamDeck. All rights reserved.
# @FileName   : rsa_tool.py
# @Author     : yaowei
# @Version    : 0.0.1
# @Date       : 2022/11/12 16:27
# @Description: write some description here
# @Update    :
# @Software   : PyCharm

import base64

import rsa.common
from loguru import logger

try:
    from Crypto.PublicKey import RSA
except Exception as ie:
    logger.info(ie)
    from crypto.PublicKey import RSA


def _read_pem(path: str = '../tools/key/private.pem'):
    with open(path, 'r') as f:
        _key = f.read()
        return RSA.importKey(_key)


def rsa_decrypt(pri_key, bytes_string):
    pri_key = rsa.PrivateKey(pri_key.n, pri_key.e, pri_key.d, pri_key.p, pri_key.q)
    key_length = rsa.common.byte_size(pri_key.n)
    if len(bytes_string) % key_length != 0:
        return None

    count = len(bytes_string) // key_length
    d_cty_bytes = b''

    for i in range(count):
        start = key_length * i
        size = key_length
        content = bytes_string[start: start + size]
        d_crypto = rsa.decrypt(content, pri_key)
        d_cty_bytes = d_cty_bytes + d_crypto
    return d_cty_bytes


# 传递字符串,默认使用key文件夹下的private.pem进行解密
def str_decrypt(msg: str, pri_key: RSA.RsaKey = _read_pem()):
    encrypted_bytes = base64.b64decode(msg)
    d_crypto_bytes = rsa_decrypt(pri_key, encrypted_bytes)
    if not d_crypto_bytes:
        return None
    return d_crypto_bytes.decode()


# 字符串转二进制数据,结果中不带0b
def str2bin_encode(data):
    return ' '.join([bin(ord(c)).replace('0b', '') for c in data])


# 二进制数据还原为十进制字符串
def bin2str_decode(msg):
    return ''.join([chr(i) for i in [int(b, 2) for b in msg.split(' ')]])
