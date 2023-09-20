import os
from typing import List, Optional

from amiyabot import Message
from amiyabot.builtin.messageChain import Chain
from amiyabot.database import connect_database, ModelClass, table
from amiyabot.factory import BotHandlerFactory
from peewee import AutoField, CharField, BooleanField

from core import AmiyaBotPluginInstance, log, bot as main_bot

from .helper import ArknightsHelper

curr_dir = os.path.dirname(__file__)
message_record = {}
db = connect_database('resource/plugins/tools/skland.db')


class SignBaseModel(ModelClass):
    class Meta:
        database = db


@table
class SklandSign(SignBaseModel):
    id: int = AutoField()
    user_id: str = CharField()
    open: bool = BooleanField(default=False)
    remark: str = CharField(null=True)

    @staticmethod
    def get_skland_sign(user_id: str) -> Optional['SklandSign']:
        return SklandSign.get_or_none(SklandSign.user_id == user_id)

    @staticmethod
    def set_skland_sign(user_id: str, open_: Optional[bool] = None, cred: Optional[str] = None):
        result = SklandSign.get_or_none(SklandSign.user_id == user_id)
        if result:
            if open_:
                result.open = open_
            if cred:
                result.remark = cred
            return result.save()
        else:
            return SklandSign.create(user_id=user_id, open=open_)

    @staticmethod
    def get_skland_sign_open() -> List['SklandSign']:
        return SklandSign.select().where(SklandSign.open == True)


class ToolsPluginInstance(AmiyaBotPluginInstance):
    pass


bot = ToolsPluginInstance(
    name='森空岛签到插件',
    version='1.1',
    plugin_id='amiyabot-skland-sign',
    plugin_type='tools',
    description='森空岛每日签到',
    document=f'{curr_dir}/README.md',
    instruction=f'{curr_dir}/README.md',
    global_config_default=f'{curr_dir}/global_config_default.json',
    global_config_schema=f'{curr_dir}/global_config_schema.json',
)


# 每个群聊存储一份data用于发送消息
async def record_msg(data: Message):
    global message_record
    message_record[data.channel_id] = data
    return False


@bot.on_message(verify=record_msg, check_prefix=False)
async def auction_offer(data: Message):
    pass


async def groups_send_message(groups: List[str], msg: str, markdown: bool = True):
    for group_id_ in groups:
        sp = group_id_.split('_')
        if sp[0] in main_bot:
            try:
                data = message_record[sp[1]]
                if markdown:
                    await data.send(Chain(data, at=False).markdown(msg, is_dark=True))
                else:
                    await data.send(Chain(data, at=False).text(msg))
            except KeyError:
                if markdown:
                    await main_bot[sp[0]].send_message(Chain().markdown(msg, is_dark=True), channel_id=sp[1])
                else:
                    await main_bot[sp[0]].send_message(Chain().text(msg), channel_id=sp[1])


async def group_send_message(group: str, msg: str, markdown: bool = True):
    sp = group.split('_')
    if sp[0] in main_bot:
        try:
            data = message_record[sp[1]]
            if markdown:
                await data.send(Chain(data, at=False).markdown(msg, is_dark=True))
            else:
                await data.send(Chain(data, at=False).text(msg))
        except KeyError:
            if markdown:
                await main_bot[sp[0]].send_message(Chain().markdown(msg, is_dark=True), channel_id=sp[1])
            else:
                await main_bot[sp[0]].send_message(Chain().text(msg), channel_id=sp[1])


@bot.on_message(keywords=['设置凭证'], allow_direct=True, level=5)
async def set_skland(data: Message):
    res = await data.wait(Chain(data).image(ArknightsHelper.tip()).text(
        '森空岛网址: \nhttps://www.skland.com/\n方法二代码:\nlocalStorage.getItem("SK_OAUTH_CRED_KEY");\n方法三代码:\njavascript:prompt(undefined, localStorage.getItem("SK_OAUTH_CRED_KEY"));'),
        max_time=120)
    if res:
        await res.recall()
        cred = res.text_original
        SklandSign.set_skland_sign(data.user_id, cred=cred)
        return Chain(data).text('设置成功')
    return Chain(data).text('操作超时')


@bot.on_message(keywords=['方舟签到'], allow_direct=True, level=5)
async def sign_skland(data: Message):
    async def true_or_false(message: Message):
        if message.text_original in ['是', '否']:
            return True

    user_id = data.user_id
    sign = SklandSign.get_skland_sign(user_id)
    if sign and sign.remark:
        if sign.open:
            reply = await data.wait(Chain(data).text('森空岛签到已开启，是否关闭？(是/否)'), data_filter=true_or_false, max_time=20)
            if reply:
                if reply.text_original == '是':
                    SklandSign.set_skland_sign(user_id, open_=False)
                    return Chain(data).text('森空岛签到已关闭')
                reply = await data.wait(Chain(data).text('是否立即签到？(是/否)'), data_filter=true_or_false, max_time=20)
                if reply and reply.text_original == '是':
                    msg, _ = await ArknightsHelper(sign.remark).sign()
                    return Chain(data).text(msg)
            return Chain(data).text('操作已取消')
        reply = await data.wait(Chain(data).text('森空岛签到已关闭，是否开启？(是/否)'), data_filter=true_or_false, max_time=20)
        if reply and reply.text_original == '是':
            SklandSign.set_skland_sign(user_id, open_=True)
            reply = await data.wait(Chain(data).text('森空岛签到已开启，是否立即签到？(是/否)'), data_filter=true_or_false, max_time=20)
            if reply and reply.text_original == '是':
                msg, _ = await ArknightsHelper(sign.remark).sign()
                return Chain(data).text(msg)
        return Chain(data).text('操作已取消')
    return Chain(data).text('博士，您尚未绑定 Cred，请发送 “兔兔设置凭证” 查看绑定说明。')


@bot.timed_task(sub_tag='skland_sign', trigger='cron', hour=6)
async def skland_sign(instance: BotHandlerFactory):
    msgs = []
    users = SklandSign.get_skland_sign_open()
    for user in users:
        user_id = user.user_id
        cred = user.remark
        if cred:
            msg, _ = await ArknightsHelper(cred).sign()
            msgs.append(f'用户 {user_id} 签到结果: {msg}')
        else:
            msgs.append(f'用户 {user_id} 未绑定 Cred')
    if msgs:
        config = bot.get_config('skland_sign')
        if config:
            groups = []
            for group in config:
                groups.append(f'{group["appid"]}_{group["group"]}')
            await groups_send_message(groups, '\n\n'.join(msgs))
