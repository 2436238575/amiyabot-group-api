import os

from amiyabot import Message, log

from core import AmiyaBotPluginInstance
from .server_api import server_state_flags  # 必须执行这个空引入来引入服务器代码

curr_dir = os.path.dirname(__file__)

class _PluginInstance(AmiyaBotPluginInstance):
    def install(self):
        pass
    def load(self):
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
