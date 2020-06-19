# -*- coding: utf-8 -*-
"""
使用方法:
    # 通过名字创建机器人
    name = "精益运营推进小组"
    r = Robot(name)

    # 通过 api,key 创建机器人
    r = Robot(api, key)

    # 发送普通文本或者 markdown 消息
    r.send_msg(text) or r.send_markdown(title,text)
"""

import requests
import json
import time
import hmac
import hashlib
import base64
import urllib

from os import environ

ROBOTS = r"\documents\auto_message_maneger\robots.json"


def read_json(path):
    fp = open(path, encoding="utf-8")
    result = json.load(fp)
    fp.close()
    return result


def getSign(key):
    timestamp = int(round(time.time() * 1000))
    secret = key
    secret_enc = secret.encode()
    string_to_sign = "{}\n{}".format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode()
    hmac_code = hmac.new(
        secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


class Robot(object):
    def __init__(self, api, key=None):
        if "https://" not in api:
            try:
                path = environ["USERPROFILE"] + ROBOTS
                info = read_json(path)[api]
                api = info["api"]
                key = info["key"]
            except KeyError:
                raise KeyError('"%s" 既未包含 "https://" 字符, 也不是有效的机器人名称' % api)
        self.headers = {"Content-Type": "application/json;charset=utf-8"}
        pwd = getSign(key)
        self.url = api + "&timestamp={}&sign={}".format(pwd[0], pwd[1])

    def send_text(self, text, at=[]):
        m = {
            "msgtype": "text",
            "text": {"content": text},
            "at": {"atMobiles": at, "isAtAll": False},
        }
        response = requests.post(self.url, json.dumps(m), headers=self.headers)
        return json.loads(response.content)

    def send_markdown(self, title, text, at=[]):
        m = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
            "at": {"atMobiles": at, "isAtAll": False},
        }
        response = requests.post(self.url, json.dumps(m), headers=self.headers)
        return json.loads(response.content)

    def send_msg(self, msg, at=[]):
        m = {"at": {"atMobiles": at, "isAtAll": False}}
        m.update(msg)
        response = requests.post(self.url, json.dumps(m), headers=self.headers)
        return json.loads(response.content)


def broadcast(api, key, msg, at=[]):
    try:
        r = Robot(api, key)
        return r.send_msg(msg, at)
    except KeyError:
        return {"errmsg": f"{api} 不是有效的机器人.", "errcode": 404}


def broadcasttxt(api, key, message, at=[]):
    r = Robot(api, key)
    return r.send_text(message, at)


def boradcastmkd(api, key, title, text, at=[]):
    r = Robot(api, key)
    return r.send_markdown(title, text, at)


# b'{"errcode":0,"errmsg":"ok"}'
# b'{"errcode":300001,"errmsg":"message param text is null "}'
