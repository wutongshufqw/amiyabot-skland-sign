try:
    import ujson as json
except ImportError:
    import json
from pathlib import Path
from typing import Tuple

import requests

app_code = '4ca99fa6b56cc2ba'
curr_path = Path(__file__).parent
header_path = curr_path / 'header.json'
header_login_path = curr_path / 'header_login.json'
# 使用token获得认证代码
grant_code_url = "https://as.hypergryph.com/user/oauth2/v2/grant"
# 使用认证代码获得cred
cred_code_url = "https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code"
# 绑定的角色url
binding_url = "https://zonai.skland.com/api/v1/game/player/binding"
# 签到url
sign_url = "https://zonai.skland.com/api/v1/game/attendance"


class ArknightsException(Exception):
    pass


class ArknightsHelper:
    def __init__(self, cred: str):
        self.cred = cred

    @property
    def header_login(self) -> dict:
        with open(header_login_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @property
    def header(self) -> dict:
        with open(header_path, 'r', encoding='utf-8') as f:
            header = json.load(f)
            header['cred'] = self.cred
            return header

    def get_binding_list(self) -> list:
        v = []
        resp = requests.get(binding_url, headers=self.header).json()
        if resp['code'] != 0:
            msg = f"请求角色列表出现问题: {resp['message']}"
            if resp.get('message') == '用户未登录':
                msg += '\n用户登录可能失效了, 请重新运行此程序!'
            raise ArknightsException(msg)
        for i in resp['data']['list']:
            if i.get('appCode') != 'arknights':
                continue
            v.extend(i.get('bindingList'))
        return v

    def do_sign(self) -> str:
        characters = self.get_binding_list()
        msgs = []
        for i in characters:
            body = {
                'uid': i.get('uid'),
                'gameId': 1
            }
            resp = requests.post(sign_url, headers=self.header, json=body).json()
            if resp['code'] != 0:
                msgs.append(f'角色{i.get("nickName")}({i.get("channelName")})签到失败了!原因: {resp.get("message")}')
                continue
            awards = resp['data']['awards']
            for j in awards:
                res = j['resource']
                msgs.append(
                    f'角色{i.get("nickName")}({i.get("channelName")})签到成功, 获得了{res["name"]}×{j.get("count") or 1}'
                )
        return '\n\n'.join(msgs)

    async def sign(self) -> Tuple[str, str]:
        """签到
        :return: msg: 消息, info: 状态 (success, warning, error)
        """
        try:
            msgs = self.do_sign()
            return msgs, 'success'
        except ArknightsException as e:
            return f'签到失败了, 请检查cred是否正确 -> 发送 [兔兔设置凭证] 查看使用说明, 失败原因: {e.__str__()}', 'error'
        except Exception as e:
            return f'签到失败了, 原因: {e}', 'error'

    @staticmethod
    def tip() -> bytes:
        pic_path = curr_path / 'tip.png'
        return pic_path.read_bytes()
