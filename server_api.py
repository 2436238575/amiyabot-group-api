import hashlib
import inspect
import os
import re
import time
from typing import Any

from flask import request
from amiyabot import Chain
from pydantic import BaseModel

from core import app, bot as main_bot
from core.database.bot import DisabledFunction
from core.database.group import GroupActive
from .game_registry import game_registry


_latest_messages: dict[tuple[str, str], Any] = {}
_capability_handlers: dict[str, Any] = {}

_HIDDEN_HELP_PLUGIN_IDS = {
    'amiyabot-admin',
    'amiyabot-arknights-gamedata',
    'amiyabot-blm-library',
    'amiyabot-hsyhhssyy-chatgpt',
    'amiyabot-talking',
    'im-skin-resource',
    'kkss-call-limit',
    'kkss-pool-switch',
}


def remember_message(data) -> None:
    key = (str(getattr(data, "channel_id", "")), str(getattr(data, "user_id", "")))
    _latest_messages[key] = data


def _json_value(value):
    if isinstance(value, re.Pattern):
        return {"type": "regex", "value": value.pattern}
    if hasattr(value, "content"):
        return {"type": "equal", "value": value.content}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value if isinstance(value, (str, int, float, bool)) or value is None else str(value)


def _build_capabilities() -> list[dict[str, Any]]:
    _capability_handlers.clear()
    result = []
    for plugin_id, plugin in main_bot.plugins.items():
        if plugin_id == "amiyabot-group-api":
            continue
        try:
            handlers = plugin.get_container("message_handlers")
        except (AttributeError, KeyError):
            continue
        for index, handler in enumerate(handlers):
            function = getattr(handler, "function", None)
            if function is None:
                continue
            source = f"{plugin_id}:{function.__module__}:{function.__qualname__}:{index}"
            capability_id = hashlib.sha256(source.encode()).hexdigest()[:24]
            callable_handler = len(inspect.signature(function).parameters) == 1
            item = {
                "capability_id": capability_id,
                "plugin_id": plugin_id,
                "plugin_name": getattr(plugin, "name", plugin_id),
                "name": getattr(function, "__name__", capability_id),
                "description": inspect.getdoc(function) or "",
                "keywords": _json_value(getattr(handler, "keywords", None)),
                "match_mode": "dynamic" if getattr(handler, "custom_verify", None) else "static",
                "callable": callable_handler,
                "parameters": [],
            }
            result.append(item)
            _capability_handlers[capability_id] = (plugin, handler)
    return result


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
class Bridge:
    @app.route('/bridge/v1/game-sessions', method='get')
    async def get_game_sessions(self):
        return app.response({
            "generation": game_registry.generation,
            "updated_at": int(time.time()),
            "sessions": game_registry.snapshot(),
        })

    @app.route('/bridge/v1/capabilities', method='get')
    async def get_capabilities(self):
        return app.response({"capabilities": _build_capabilities()})

    @app.route('/bridge/v1/help', method='get')
    async def get_help(self, group_id: int = None):
        """返回仿 AmiyaBot「功能/帮助」菜单所需的当前群插件清单。"""
        if group_id is None:
            group_id = request.args.get('group_id')
        disabled = set()
        if group_id is not None:
            disabled = {
                str(row.function_id)
                for row in DisabledFunction.select().where(
                    DisabledFunction.channel_id == str(group_id)
                )
            }
        plugins = []
        for plugin_id, plugin in sorted(main_bot.plugins.items(), key=lambda pair: getattr(pair[1], 'name', pair[0])):
            if plugin_id in _HIDDEN_HELP_PLUGIN_IDS or plugin_id == 'amiyabot-group-api':
                continue
            plugins.append({
                'plugin_id': plugin_id,
                'name': getattr(plugin, 'name', plugin_id),
                'version': str(getattr(plugin, 'version', '') or ''),
                'description': str(getattr(plugin, 'description', '') or ''),
                'enabled': plugin_id not in disabled,
            })
        return app.response({'group_id': group_id, 'plugins': plugins})

    @app.route('/bridge/v1/help/{plugin_id}', method='get')
    async def get_help_detail(self, plugin_id: str):
        """返回 AmiyaBot 帮助菜单中指定插件的使用文档。"""
        plugin = main_bot.plugins.get(plugin_id)
        if plugin is None or plugin_id in _HIDDEN_HELP_PLUGIN_IDS or plugin_id == 'amiyabot-group-api':
            return app.response({'error': 'plugin_not_found'}, 404)
        document = getattr(plugin, 'instruction', None) or getattr(plugin, 'document', None)
        content = document
        if content and isinstance(content, str):
            try:
                if os.path.isfile(content):
                    base, extension = os.path.splitext(content)
                    public_document = f'{base}-public{extension}'
                    if os.path.isfile(public_document):
                        content = public_document
                    with open(content, 'r', encoding='utf-8') as file:
                        content = file.read()
            except OSError:
                content = None
        return app.response({
            'plugin_id': plugin_id,
            'name': getattr(plugin, 'name', plugin_id),
            'version': str(getattr(plugin, 'version', '') or ''),
            'description': str(getattr(plugin, 'description', '') or ''),
            'content': content or '该插件没有提供详细使用文档。',
        })

    @app.route('/bridge/v1/capabilities/{capability_id}/invoke', method='post')
    async def invoke_capability(self, capability_id: str, data: dict):
        capabilities = _build_capabilities()
        item = next((value for value in capabilities if value["capability_id"] == capability_id), None)
        if item is None:
            return app.response({"error": "capability_not_found"}, 404)
        if not item["callable"]:
            return app.response({"error": "capability_not_callable"}, 409)
        context = data.get("context") or {}
        key = (str(context.get("group_id", "")), str(context.get("user_id", "")))
        message = _latest_messages.get(key)
        if message is None:
            return app.response({"error": "message_context_not_found"}, 409)
        _, handler = _capability_handlers[capability_id]
        try:
            reply = await handler.action(message)
            if reply:
                if isinstance(reply, str):
                    reply = Chain(message, at=False).text(reply)
                await message.send(reply)
            return app.response({"handled": bool(reply), "result": str(reply or "")})
        except Exception as exc:
            return app.response({"error": "capability_execution_failed", "message": str(exc)}, 500)


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
