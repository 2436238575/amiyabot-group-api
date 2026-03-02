import time

from flask import request
from pydantic import BaseModel

from core import app, bot as main_bot
from core.database.bot import DisabledFunction
from core.database.group import GroupActive


class SetGroupActiveRequest(BaseModel):
    group_id: int
    active: bool


class GetGroupFunctionListRequest(BaseModel):
    group_id: int


class SetGroupFunctionRequest(BaseModel):
    group_id: int
    plugin_id: str
    disabled: bool


server_state_flags = {
    "ready": False
}


@app.controller
class Group:
    @app.route('/group/getGroupActiveList', method='get')
    async def get_group_active_list(self):
        """获取群启用状态列表"""
        try:
            groups = GroupActive.select()
            data = []
            for group in groups:
                data.append({
                    "group_id": int(group.group_id),
                    "active": bool(group.active),
                    "sleep_time": group.sleep_time
                })

            return app.response(data)
        except Exception as e:
            return app.response({}, 500)

    @app.route('/group/setGroupActive', method='post')
    async def set_group_active(self, data: SetGroupActiveRequest):
        """设置群启用状态"""
        try:
            # 验证参数
            if data.group_id is None or data.active is None:
                return app.response({}, 400)

            # 更新或创建群组状态
            group, created = GroupActive.get_or_create(
                group_id=str(data.group_id),
                defaults={'active': int(data.active), 'sleep_time': 0}
            )

            if not created:
                if data.active:
                    # 如果激活，清除睡眠时间
                    GroupActive.update(active=int(data.active), sleep_time=0).where(
                        GroupActive.group_id == str(data.group_id)
                    ).execute()
                else:
                    # 如果停用，记录睡眠时间
                    GroupActive.update(active=int(data.active), sleep_time=int(time.time())).where(
                        GroupActive.group_id == str(data.group_id)
                    ).execute()

            return app.response({
                "status": True
            })
        except Exception as e:
            return app.response({}, 500)

    @app.route('/group/getGroupFunctionList', method='get')
    async def get_group_function_list(self, group_id: int = None):
        """获取群功能启用状态列表"""
        try:
            # 从路由参数或查询参数中获取group_id
            if group_id is None:
                # 尝试从请求上下文获取
                group_id_param = request.args.get('group_id')
                if group_id_param is not None:
                    group_id = int(group_id_param)

            if group_id is None:
                return app.response({"code": 400, "data": {}, "message": "Missing group_id parameter"})

            group_str_id = str(group_id)

            # 获取群组中被禁用的功能列表
            disabled_functions = DisabledFunction.select().where(
                DisabledFunction.channel_id == group_str_id
            )
            disabled_plugin_ids = {df.function_id for df in disabled_functions}

            # 获取所有可用插件
            all_plugins = []
            for plugin_id, plugin in main_bot.plugins.items():
                # 跳过当前的插件本身
                if plugin_id == 'amiyabot-group-api':
                    continue

                plugin_info = {
                    "name": plugin.name,
                    "plugin_id": plugin_id,
                    "disabled": plugin_id in disabled_plugin_ids
                }
                all_plugins.append(plugin_info)

            # 构建响应数据
            result_data = {
                "group_id": group_id,
            }

            # 使用索引作为键，从0开始递增
            for idx, plugin_info in enumerate(all_plugins):
                result_data[str(idx)] = plugin_info

            return app.response(result_data)
        except (ValueError, TypeError):
            return app.response({"code": 400, "data": {}, "message": "Invalid group_id parameter"})  # 参数类型错误
        except Exception as e:
            return app.response({"code": 500, "data": {}, "message": str(e)})

    @app.route('/group/setFunctionActive', method='post')
    async def set_group_function(self, data: SetGroupFunctionRequest):
        """设置群功能启用状态"""
        try:
            # 验证参数
            if data.group_id is None or data.plugin_id is None or data.disabled is None:
                return app.response({}, 400)

            group_id = str(data.group_id)
            plugin_id = data.plugin_id

            # 验证插件ID是否存在
            if plugin_id not in main_bot.plugins:
                return app.response({"status": False}, 400)

            # 检查是否已经存在对应的禁用记录
            existing_record = DisabledFunction.get_or_none(
                function_id=plugin_id,
                channel_id=group_id
            )

            if data.disabled:
                # 设置为禁用状态，创建记录（如果不存在）
                if not existing_record:
                    DisabledFunction.create(
                        function_id=plugin_id,
                        channel_id=group_id
                    )
            else:
                # 设置为启用状态，删除记录（如果存在）
                if existing_record:
                    existing_record.delete_instance()

            return app.response({"status": True})
        except Exception as e:
            return app.response({}, 500)
