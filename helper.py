from typing import Tuple

import requests

app_code = '4ca99fa6b56cc2ba'
header = {
    'cred': '',
    'User-Agent': 'Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0',
    'Accept-Encoding': 'gzip',
    'Connection': 'close'
}
header_login = {
    'User-Agent': 'Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0',
    'Accept-Encoding': 'gzip',
    'Connection': 'close'
}
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


def get_cred(grant_code: str):
    resp = requests.post(
        cred_code_url,
        json={
            'code': grant_code,
            'kind': 1
        },
        headers=header_login
    ).json()
    if resp['code'] != 0:
        raise ArknightsException(f'获得cred失败：{resp["message"]}')
    return resp['data']['cred']


def get_binding_list() -> list:
    v = []
    resp = requests.get(binding_url, headers=header).json()
    if resp['code'] != 0:
        msg = f"请求角色列表出现问题: {resp['message']}"
        if resp.get('message') == '用户未登录':
            msg += f'用户登录可能失效了, 请重新运行此程序!'
        raise ArknightsException(msg)
    for i in resp['data']['list']:
        if i.get('appCode') != 'arknights':
            continue
        v.extend(i.get('bindingList'))
    return v


def do_sign(cred: str) -> str:
    header['cred'] = cred
    characters = get_binding_list()
    msgs = []
    for i in characters:
        body = {
            'uid': i.get('uid'),
            'gameId': 1
        }
        resp = requests.post(sign_url, headers=header, json=body).json()
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


class ArknightsHelper:
    def __init__(self, token: str):
        self.token = token

    async def sign(self) -> Tuple[str, str]:
        """签到
        :return: msg: 消息, info: 状态 (success, warning, error)
        """
        try:
            msgs = do_sign(self.get_cred_by_token())
            return msgs, 'success'
        except ArknightsException as e:
            return f'签到失败了, 请检查token是否正确 -> 发送 [兔兔绑定] 查看使用说明, 失败原因: {e.__str__()}', 'error'
        except Exception as e:
            return f'签到失败了, 原因: {e}', 'error'

    def get_cred_by_token(self) -> str:
        grant_code = self.get_grant_code()
        return get_cred(grant_code)

    def get_grant_code(self) -> str:
        response = requests.post(
            grant_code_url,
            json={
                'appCode': app_code,
                'token': self.token,
                'type': 0
            },
            headers=header_login
        )
        resp = response.json()
        if response.status_code != 200:
            raise ArknightsException(f'获得认证代码失败: {resp}')
        if resp.get('status') != 0:
            raise ArknightsException(f'获得认证代码失败: {resp["msg"]}')
        return resp['data']['code']

