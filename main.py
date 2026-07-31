import os

from amiyabot import Message, log

from core import AmiyaBotPluginInstance
from .game_registry import game_registry
from .server_api import remember_message, server_state_flags  # 必须执行这个空引入来引入服务器代码

curr_dir = os.path.dirname(__file__)

class _PluginInstance(AmiyaBotPluginInstance):
    def install(self):
        pass
    def load(self):
        game_registry.reset()
        server_state_flags["ready"] = True
        log.info('GroupAPIPluginInstance Ready')

bot = _PluginInstance(
    name='API-群聊管理',
    version='0.0.1',
    plugin_id='amiyabot-group-api',
    plugin_type='',
    description='提供群聊管理相关的 API 接口',
    document=f'{curr_dir}/README.md'

)

@bot.message_before_handle
async def _(data: Message, factory_name: str, instance):
    server_state_flags["live"] = True


@bot.message_created
async def _remember(data: Message, instance):
    remember_message(data)
