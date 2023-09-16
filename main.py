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
    def get_skland_sign(user_id: str) -> bool:
        result = SklandSign.get_or_none(SklandSign.user_id == user_id)
        if result:
            return result.open
        else:
            return False

    @staticmethod
    def set_skland_sign(user_id: str, open_: bool):
        result = SklandSign.get_or_none(SklandSign.user_id == user_id)
        if result:
            result.open = open_
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
    version='1.0',
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


@bot.on_message(keywords=['方舟签到'], allow_direct=True, level=5)
async def sign_skland(data: Message):
    async def true_or_false(message: Message):
        if message.text_original in ['是', '否']:
            return True

    user_id = data.user_id
    if 'amiyabot-skland' in main_bot.plugins:
        plugin = main_bot.plugins['amiyabot-skland']
        token: Optional[str] = await plugin.get_token(user_id)
        if token:
            if SklandSign.get_skland_sign(user_id):
                reply = await data.wait(Chain(data).text('森空岛签到已开启，是否关闭？(是/否)'), data_filter=true_or_false, max_time=20)
                if reply:
                    if reply.text_original == '是':
                        SklandSign.set_skland_sign(user_id, False)
                        return Chain(data).text('森空岛签到已关闭')
                    else:
                        reply = await data.wait(Chain(data).text('是否立即签到？(是/否)'), data_filter=true_or_false, max_time=20)
                        if reply:
                            if reply.text_original == '是':
                                msg, _ = await ArknightsHelper(token).sign()
                                return Chain(data).text(msg)
                return Chain(data).text('操作已取消')
            else:
                reply = await data.wait(Chain(data).text('森空岛签到已关闭，是否开启？(是/否)'), data_filter=true_or_false, max_time=20)
                if reply:
                    if reply.text_original == '是':
                        SklandSign.set_skland_sign(user_id, True)
                        reply = await data.wait(Chain(data).text('森空岛签到已开启，是否立即签到？(是/否)'), data_filter=true_or_false, max_time=20)
                        if reply:
                            if reply.text_original == '是':
                                msg, info = await ArknightsHelper(token).sign()
                                return Chain(data).text(msg)
                return Chain(data).text('操作已取消')
        else:
            return Chain(data).text('博士，您尚未绑定 Token，请发送 “兔兔绑定” 查看绑定说明。')
    else:
        return Chain(data).text('兔兔尚未安装森空岛插件，请联系管理员安装插件。')


@bot.timed_task(sub_tag='skland_sign', trigger='cron', hour=6)
async def skland_sign(instance: BotHandlerFactory):
    if 'amiyabot-skland' in main_bot.plugins:
        msgs = []
        plugin = main_bot.plugins['amiyabot-skland']
        users = SklandSign.get_skland_sign_open()
        for user in users:
            user_id = user.user_id
            token: Optional[str] = await plugin.get_token(user_id)
            if token:
                if SklandSign.get_skland_sign(user_id):
                    msg, _ = await ArknightsHelper(token).sign()
                    msgs.append(f'用户 {user_id} 签到结果: {msg}')
            else:
                msgs.append(f'用户 {user_id} 未绑定 Token')
        if msgs:
            config = bot.get_config('skland_sign')
            if config:
                groups = []
                for group in config:
                    groups.append(f'{group["appid"]}_{group["group"]}')
                await groups_send_message(groups, '\n\n'.join(msgs))
