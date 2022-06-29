from src.modules.group_info import GroupInfo
from src.params import GroupSetting

from . import _jx3_event as Event


async def get_ws_status(group_id: int,
                        event: Event.RecvEvent
                        ) -> bool:
    '''
    说明:
        获取ws通知开关，robot为关闭时返回False

    参数:
        * `group_id`：QQ群号
        * `event`：接收事件类型

    返回:
        * `bool`：ws通知开关
    '''

    bot_status = await GroupInfo.get_bot_status(group_id)
    if not bot_status:
        return False

    if isinstance(event, Event.ServerStatusEvent):
        recv_type = GroupSetting.开服推送
    if isinstance(event, Event.NewsRecvEvent):
        recv_type = GroupSetting.新闻推送
    if isinstance(event, Event.SerendipityEvent):
        recv_type = GroupSetting.奇遇推送
    if isinstance(event, Event.HorseRefreshEvent) or isinstance(event, Event.HorseCatchedEvent):
        recv_type = GroupSetting.抓马监控
    if isinstance(event, Event.FuyaoRefreshEvent) or isinstance(event, Event.FuyaoNamedEvent):
        recv_type = GroupSetting.扶摇监控

    return await GroupInfo.get_config_status(group_id, recv_type)
