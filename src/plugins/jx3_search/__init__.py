import io
import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import NoReturn, Optional

import requests
from PIL import Image
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import Depends, RegexDict
from nonebot.plugin import PluginMetadata

from src.config import jx3api_v2_config
from src.internal.jx3api import JX3API
from src.internal.jx3apiV2 import JX3APIV2
from src.modules.baizhanyiwenlu_info import BaiZhanYiWenLuInfo
from src.modules.group_info import GroupInfo
from src.modules.search_record import SearchRecord
from src.modules.ticket_info import TicketInfo
from src.params import PluginConfig, user_matcher_group
from src.utils.browser import browser
from src.utils.log import logger
from . import data_source as source
from .config import JX3PROFESSION

__plugin_meta__ = PluginMetadata(
    name="剑三查询", description="剑三游戏查询，数据源使用jx3api", usage="参考“帮助”", config=PluginConfig()
)

api = JX3API()
"""jx3api接口实例"""
api_v2 = JX3APIV2()
"""jx3 万宝楼接口实例"""


# ----------------------------------------------------------------
#   正则枚举，已实现的查询功能
# ----------------------------------------------------------------


class REGEX(Enum):
    """正则枚举"""

    日常任务 = r"^日常$|^日常 (?P<server>[\S]+)$"
    开服检查 = r"^开服$|^开服 (?P<server>[\S]+)$"
    金价比例 = r"^金价$|^金价 (?P<server>[\S]+)$"
    推荐小药 = r"^小药 (?P<value1>[\S]+)$|^(?P<value2>[\S]+)小药$"
    推荐装备 = r"^配装 (?P<value1>[\S]+)$|^(?P<value2>[\S]+)配装$"
    查宏命令 = r"^宏 (?P<value1>[\S]+)$|^(?P<value2>[\S]+)宏$"
    阵眼效果 = r"^阵眼 (?P<value1>[\S]+)$|^(?P<value2>[\S]+)阵眼$"
    物品价格 = r"^物价 (?P<value1>[\S]+)$"
    随机骚话 = r"^骚话$"
    奇遇前置 = r"^(?:(?:前置)|(?:条件)) (?P<value1>[\S]+)$"
    奇遇攻略 = r"^攻略 (?P<value1>[\S]+)$|^(?P<value2>[\S]+)攻略$"
    更新公告 = r"^更新$|^公告$|^更新公告$"
    奇遇查询 = r"^查询 (?P<value1>[\S]+)$|^查询 (?P<server>[\S]+) (?P<value2>[\S]+)$"
    奇遇统计 = r"^奇遇 (?P<value1>[\S]+)$|^奇遇 (?P<server>[\S]+) (?P<value2>[\S]+)$"
    奇遇汇总 = r"^汇总$|^汇总 (?P<server>[\S]+)$"
    比赛战绩 = r"^战绩 (?P<value1>[\S]+)$|^战绩 (?P<server>[\S]+) (?P<value2>[\S]+)$"
    装备属性 = r"^(?:(?:装备)|(?:属性)) (?P<value1>[\S]+)$|^(?:(?:装备)|(?:属性)) (?P<server>[\S]+) (?P<value2>[\S]+)$"
    烟花记录 = r"^烟花 (?P<value1>[\S]+)$|^烟花 (?P<server>[\S]+) (?P<value2>[\S]+)$"
    招募查询 = r"^招募$|^招募 (?P<server1>[\S]+)$|^招募 (?P<server2>[\S]+) (?P<keyword>[\S]+)$"
    沙盘查询 = r"^沙盘$|^沙盘 (?P<server>[\S]+)$"
    资历榜 = r"^资历榜$|^资历榜 (?P<server1>[\S]+)$|^资历榜 (?P<server2>[\S]+) (?P<keyword>[\S]+)$"
    声望榜 = r"^(?P<type1>声望榜)$|^(?P<type2>声望榜) (?P<server>[\S]+)$"
    老江湖 = r"^(?P<type1>老江湖)$|^(?P<type2>老江湖) (?P<server>[\S]+)$"
    兵甲榜 = r"^(?P<type1>兵甲榜)$|^(?P<type2>兵甲榜) (?P<server>[\S]+)$"
    名师榜 = r"^(?P<type1>名师榜)$|^(?P<type2>名师榜) (?P<server>[\S]+)$"
    战阶榜 = r"^(?P<type1>战阶榜)$|^(?P<type2>战阶榜) (?P<server>[\S]+)$"
    薪火榜 = r"^(?P<type1>薪火榜)$|^(?P<type2>薪火榜) (?P<server>[\S]+)$"
    梓行榜 = r"^(?P<type1>梓行榜)$|^(?P<type2>梓行榜) (?P<server>[\S]+)$"
    爱心榜 = r"^(?P<type1>爱心榜) (?P<value1>[\S]+)$|^(?P<type2>爱心榜) (?P<server>[\S]+) (?P<value2>[\S]+)$"
    神兵榜 = r"^(?P<type1>神兵榜) (?P<value1>[\S]+)$|^(?P<type2>神兵榜) (?P<server>[\S]+) (?P<value2>[\S]+)$"
    试炼榜 = r"^试炼榜 (?P<value1>[\S]+)$|^试炼榜 (?P<server>[\S]+) (?P<value2>[\S]+)$"
    百战异闻录 = r"^百战$|^百战 (?P<server>[\S]+)$"


# ----------------------------------------------------------------
#   matcher列表，定义查询的mathcer
# ----------------------------------------------------------------
daily_query = user_matcher_group.on_regex(pattern=REGEX.日常任务.value)
server_query = user_matcher_group.on_regex(pattern=REGEX.开服检查.value)
gold_query = user_matcher_group.on_regex(pattern=REGEX.金价比例.value)
medicine_query = user_matcher_group.on_regex(pattern=REGEX.推荐小药.value)
equip_group_query = user_matcher_group.on_regex(pattern=REGEX.推荐装备.value)
macro_query = user_matcher_group.on_regex(pattern=REGEX.查宏命令.value)
zhenyan_query = user_matcher_group.on_regex(pattern=REGEX.阵眼效果.value)
condition_query = user_matcher_group.on_regex(pattern=REGEX.奇遇前置.value)
strategy_query = user_matcher_group.on_regex(pattern=REGEX.奇遇攻略.value)
update_query = user_matcher_group.on_regex(pattern=REGEX.更新公告.value)
price_query = user_matcher_group.on_regex(pattern=REGEX.物品价格.value)
serendipity_query = user_matcher_group.on_regex(pattern=REGEX.奇遇查询.value)
serendipity_list_query = user_matcher_group.on_regex(pattern=REGEX.奇遇统计.value)
serendipity_summary_query = user_matcher_group.on_regex(pattern=REGEX.奇遇汇总.value)
saohua_query = user_matcher_group.on_regex(pattern=REGEX.随机骚话.value)
match_query = user_matcher_group.on_regex(pattern=REGEX.比赛战绩.value)
equip_query = user_matcher_group.on_regex(pattern=REGEX.装备属性.value)
firework_query = user_matcher_group.on_regex(pattern=REGEX.烟花记录.value)
recruit_query = user_matcher_group.on_regex(pattern=REGEX.招募查询.value)
sand_query = user_matcher_group.on_regex(pattern=REGEX.沙盘查询.value)
zili_query = user_matcher_group.on_regex(pattern=REGEX.资历榜.value)
shengwang_query = user_matcher_group.on_regex(pattern=REGEX.声望榜.value)
laojianghu_query = user_matcher_group.on_regex(pattern=REGEX.老江湖.value)
bingjia_query = user_matcher_group.on_regex(pattern=REGEX.兵甲榜.value)
mingshi_query = user_matcher_group.on_regex(pattern=REGEX.名师榜.value)
zhanjie_query = user_matcher_group.on_regex(pattern=REGEX.战阶榜.value)
xinhuo_query = user_matcher_group.on_regex(pattern=REGEX.薪火榜.value)
zixing_query = user_matcher_group.on_regex(pattern=REGEX.梓行榜.value)
aixin_query = user_matcher_group.on_regex(pattern=REGEX.爱心榜.value)
shenbing_query = user_matcher_group.on_regex(pattern=REGEX.神兵榜.value)
shilian_query = user_matcher_group.on_regex(pattern=REGEX.试炼榜.value)
help = user_matcher_group.on_regex(pattern=r"^帮助$")
baizhan_query = user_matcher_group.on_regex(pattern=REGEX.百战异闻录.value)


# ----------------------------------------------------------------
#   Dependency，用来获取相关参数及冷却实现
# ----------------------------------------------------------------


def get_server() -> str:
    """
    说明:
        Dependency，获取匹配字符串中的server，如果没有则获取群绑定的默认server
    """

    async def dependency(
            matcher: Matcher, event: GroupMessageEvent, regex_dict: dict = RegexDict()
    ) -> str:

        _server = regex_dict.get("server")
        if _server:
            server = api.app_server(name=_server)
            if not server:
                msg = f"未找到服务器[{_server}]，请验证后查询。"
                await matcher.finish(msg)
        else:
            server = await GroupInfo.get_server(event.group_id)
        return server

    return Depends(dependency)


def get_value() -> str:
    """
    说明:
        Dependency，获取匹配字符串中的value字段
    """

    async def dependency(regex_dict: dict = RegexDict()) -> str:
        value = regex_dict.get("value1")
        return value if value else regex_dict.get("value2")

    return Depends(dependency)


def get_profession() -> str:
    """
    说明:
        Dependency，通过别名获取职业名称
    """

    async def dependency(matcher: Matcher, name: str = get_value()) -> str:
        profession = JX3PROFESSION.get_profession(name)
        if profession:
            return profession

        # 未找到职业
        msg = f"未找到职业[{name}]，请检查参数。"
        await matcher.finish(msg)

    return Depends(dependency)


def get_server_with_keyword() -> str:
    """
    说明:
        Dependency，获取server，会判断是不是keyword
    """

    async def dependency(
            matcher: Matcher, event: GroupMessageEvent, regex_dict: dict = RegexDict()
    ) -> str:
        _server = regex_dict.get("server2")
        if _server:
            server = api.app_server(name=_server)
            if not server:
                msg = f"未找到服务器[{_server}]，请验证后查询。"
                await matcher.finish(msg)
            else:
                return server
        else:
            _server = regex_dict.get("server1")
            if _server:
                # 判断server是不是keyword
                server = api.app_server(name=_server)
                if not server:
                    server = await GroupInfo.get_server(event.group_id)
            else:
                # 单招募
                server = await GroupInfo.get_server(event.group_id)
            return server

    return Depends(dependency)


def get_keyword() -> str:
    """
    说明:
        Dependency，招募查询-关键字
    """

    async def dependency(regex_dict: dict = RegexDict()) -> Optional[str]:
        if _keyword := regex_dict.get("keyword"):
            return _keyword
        if _keyword := regex_dict.get("server1"):
            if api.app_server(name=_keyword):
                keyword = None
            else:
                keyword = _keyword
        else:
            keyword = None
        return keyword

    return Depends(dependency)


def get_type() -> str:
    """
    说明:
        Dependency，排行榜-获取类型
    """

    def dependency(regex_dict: dict = RegexDict()) -> str:
        _type = regex_dict.get("type2")
        if not _type:
            _type = regex_dict.get("type1")
        match _type:
            case "声望榜":
                return "名士五十强"
            case "老江湖":
                return "老江湖五十强"
            case "兵甲榜":
                return "兵甲藏家五十强"
            case "名师榜":
                return "名师五十强"
            case "战阶榜":
                return "阵营英雄五十强"
            case "薪火榜":
                return "薪火相传五十强"
            case "梓行榜":
                return "庐园广记一百强"
            case "爱心榜":
                return "爱心帮会五十强"
            case "神兵榜":
                return "神兵宝甲五十强"
            case _:
                return ""

    return Depends(dependency)


def get_tittle() -> str:
    """
    说明:
        Dependency，排行榜-获取标题
    """

    def dependency(regex_dict: dict = RegexDict()) -> str:
        _type = regex_dict.get("type2")
        if not _type:
            _type = regex_dict.get("type1")
        match _type:
            case "声望榜":
                return "声望"
            case "老江湖":
                return "资历"
            case "兵甲榜":
                return "装分"
            case "名师榜":
                return "师徒值"
            case "战阶榜":
                return "战阶分数"
            case "薪火榜":
                return "薪火点"
            case "梓行榜":
                return "梓行点"
            case "爱心榜":
                return "爱心值"
            case "神兵榜":
                return "总装分"
            case _:
                return ""

    return Depends(dependency)


def get_camp() -> str:
    """
    说明:
        Dependency，帮会排名-获取阵营
    """

    async def dependency(matcher: Matcher, name: str = get_value()) -> str:
        match name:
            case "浩气" | "浩气盟":
                return "浩气"
            case "恶人" | "恶人谷":
                return "恶人"
            case _:
                await matcher.finish("请输入正确的阵营名！")

    return Depends(dependency)


def cold_down(name: str, cd_time: int) -> None:
    """
    说明:
        Dependency，增加命令冷却，同时会在数据库中记录一次查询

    参数:
        * `name`：app名称，相同名称会使用同一组cd
        * `cd_time`：冷却时间

    用法:
    ```
        @matcher.handle(parameterless=[cold_down(name="app", cd_time=0)])
        async def _():
            pass
    ```
    """

    async def dependency(matcher: Matcher, event: GroupMessageEvent):
        time_last = await SearchRecord.get_search_time(event.group_id, name)
        time_now = int(time.time())
        over_time = over_time = time_now - time_last
        if over_time > cd_time:
            await SearchRecord.use_search(event.group_id, name)
            return
        else:
            left_cd = cd_time - over_time
            await matcher.finish(f"[{name}]冷却中 ({left_cd})")

    return Depends(dependency)


# ----------------------------------------------------------------
#   handler列表，具体实现回复内容
# ----------------------------------------------------------------


@daily_query.handle(parameterless=[cold_down(name="日常查询", cd_time=0)])
async def _(event: GroupMessageEvent, server: str = get_server()) -> NoReturn:
    """日常查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 日常查询 | 请求：{server}"
    )
    response = await api.data_active_current(server=server)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await daily_query.finish(msg)

    data = response.data
    msg = (
        f"日常[{server}]\n"
        f'当前时间：{data.get("date", "未知")} 星期{data.get("week", "未知")}\n'
        f'【秘境大战】{data.get("war", "未知")}\n'
        f'【战场任务】{data.get("battle", "未知")}\n'
        f'【阵营任务】{data.get("camp", "未知")}\n'
        f'【公共任务】{data.get("relief", "未知")}\n'
        f'【门派事件】{data.get("school", "未知")}\n'
    )
    if data.get("draw"):
        msg += f'【美人画像】{data.get("draw")}\n'
    prestige: list[str] = data.get("prestige", [])
    team: list[str] = data.get("team")
    msg += (
        f'\n【家园声望·副本道具】\n{";".join(prestige)}'
        f"\n【武林通鉴·公共任务】\n{team[0]}"
        f"\n【武林通鉴·秘境任务】\n{team[1]}"
        f"\n【武林通鉴·团队秘境】\n{team[2]}"
    )

    await daily_query.finish(msg)


@server_query.handle(parameterless=[cold_down(name="开服查询", cd_time=0)])
async def _(event: GroupMessageEvent, server: str = get_server()) -> NoReturn:
    """开服查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 开服查询 | 请求：{server}"
    )
    response = await api.data_server_check(server=server)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await server_query.finish(msg)

    data = response.data
    status = "已开服" if data["status"] == 1 else "维护中"
    msg = f"{server} 当前状态是[{status}]"
    await server_query.finish(msg)


@baizhan_query.handle(parameterless=[cold_down(name="百战异闻录查询", cd_time=0)])
async def _(event: GroupMessageEvent) -> NoReturn:
    """开服查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 百战异闻录查询"
    )
    """先判断是否已经同步过了，如果同步过了，那就不进行查询了直接返回"""
    info = await BaiZhanYiWenLuInfo.get_info()
    if info:
        server_open_time = info['server_open_time']
        if info['valid'] and len(info['url']) > 10 and (
                time.time() - server_open_time < (60 * 60 * 24 * 7 + 60 * 60 * 4)):
            logger.info(f"<y> 从本地查询百战信息</y>")
            img = info["url"]
            await baizhan_query.finish(MessageSegment.image(Path(img)))
        if time.time() - server_open_time < (60 * 60 * 1):
            msg = f"开服一个小时后才可以查询，开服时间为 {time.localtime(server_open_time)}"
            await baizhan_query.finish(msg)
        if time.time() - server_open_time > (60 * 60 * 24 * 7 + 60 * 60 * 4):
            today = datetime.datetime.today()
            one_day = datetime.timedelta(days=today.weekday())
            today -= one_day
            timestamp = time.mktime(datetime.datetime(today.year, today.month, today.day, 15, 30, 00).timetuple())
            await BaiZhanYiWenLuInfo.update_info_when_server_reopen(open_time=timestamp)

    response = await api_v2.view_active_monster(scale=1, robot='小猫饼', token=jx3api_v2_config.api_token)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await server_query.finish(msg)
    logger.info(f"<y> 调用jx3api查询百战信息</y>")
    data = response.data
    request = requests.get(data['url'])
    img = Image.open(io.BytesIO(request.content))
    base_path = os.path.abspath('')
    base_path = os.path.join(base_path, 'template')
    base_path = os.path.join(base_path, 'baizhan')
    img_path = os.path.join(base_path, 'info.png')
    img.save(img_path)
    """把百战信息放到数据库里"""
    await BaiZhanYiWenLuInfo.update_info_when_search_success(url=img_path)
    await baizhan_query.finish(MessageSegment.image(Path(img_path)))


@gold_query.handle(parameterless=[cold_down(name="金价查询", cd_time=0)])
async def _(event: GroupMessageEvent, server: str = get_server()) -> NoReturn:
    """金价查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 金价查询 | 请求：{server}"
    )
    response = await api.data_trade_demon(server=server)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await gold_query.finish(msg)

    data: dict = response.data[0]
    date_now = datetime.now().strftime("%m-%d %H:%M")
    msg = (
        f"金价[{server}] {date_now}\n"
        f'官方平台：1元={data.get("wanbaolou")}金\n'
        f'百度贴吧：1元={data.get("tieba")}金\n'
        f'悠悠平台：1元={data.get("uu898")}金\n'
        f'嘟嘟平台：1元={data.get("dd373")}金\n'
        f'其他平台：1元={data.get("5173")}金'
    )
    await gold_query.finish(msg)


@medicine_query.handle(parameterless=[cold_down(name="小药查询", cd_time=0)])
async def _(event: GroupMessageEvent, name: str = get_profession()) -> NoReturn:
    """小药查询"""
    logger.info(f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 小药查询 | 请求：{name}")
    response = await api.data_school_snacks(name=name)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await medicine_query.finish(msg)

    data = response.data
    name = data.get("name")
    msg = (
        f"[{name}]小药：\n"
        f'增强食品：{data.get("heightenFood")}\n'
        f'辅助食品：{data.get("auxiliaryFood")}\n'
        f'增强药品：{data.get("heightenDrug")}\n'
        f'辅助药品：{data.get("auxiliaryDrug")}\n'
    )

    await medicine_query.finish(msg)


@equip_group_query.handle(parameterless=[cold_down(name="配装查询", cd_time=0)])
async def _(event: GroupMessageEvent, name: str = get_profession()) -> NoReturn:
    """配装查询"""
    logger.info(f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 配装查询 | 请求：{name}")
    response = await api.data_school_equip(name=name)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await equip_group_query.finish(msg)

    data = response.data
    msg = (
            MessageSegment.text(f'{data.get("name")}配装：\nPve装备：\n')
            + MessageSegment.image(data.get("pve"))
            + MessageSegment.text("Pvp装备：\n")
            + MessageSegment.image(data.get("pvp"))
    )
    await equip_group_query.finish(msg)


@macro_query.handle(parameterless=[cold_down(name="宏查询", cd_time=0)])
async def _(event: GroupMessageEvent, name: str = get_profession()) -> NoReturn:
    """宏查询"""
    logger.info(f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 宏查询 | 请求：{name}")
    response = await api.data_school_macro(name=name)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await macro_query.finish(msg)

    data = response.data
    msg = (
        f'宏 {data.get("name")} 更新时间：{data.get("time")}\n'
        f'{data.get("macro")}\n'
        f'奇穴：{data.get("qixue")}'
    )

    await macro_query.finish(msg)


@zhenyan_query.handle(parameterless=[cold_down(name="阵眼查询", cd_time=0)])
async def _(event: GroupMessageEvent, name: str = get_profession()) -> NoReturn:
    """阵眼查询"""
    logger.info(f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 阵眼查询 | 请求：{name}")
    response = await api.data_school_matrix(name=name)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await zhenyan_query.finish(msg)

    data = response.data
    msg = f"{name}：【{data.get('skillName')}】\n"
    descs: list[dict] = data.get("descs")
    for i in descs:
        msg += f"{i.get('name')}：{i.get('desc')}\n"
    await zhenyan_query.finish(msg)


@condition_query.handle(parameterless=[cold_down(name="前置查询", cd_time=0)])
async def _(event: GroupMessageEvent, name: str = get_value()) -> NoReturn:
    """前置查询"""
    logger.info(f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 前置查询 | 请求：{name}")
    if api.config.api_token:
        response = await api.data_luck_require(name=name)
    else:
        response = await api.data_luck_sub_require(name=name)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await condition_query.finish(msg)

    data = response.data
    url = data.get("url")
    msg = MessageSegment.image(url)
    await condition_query.finish(msg)


@strategy_query.handle(parameterless=[cold_down(name="攻略查询", cd_time=0)])
async def _(event: GroupMessageEvent, name: str = get_value()) -> NoReturn:
    """攻略查询"""
    logger.info(f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 攻略查询 | 请求：{name}")
    if api.config.api_token:
        response = await api.data_luck_strategy(name=name)
    else:
        response = await api.data_luck_sub_strategy(name=name)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await strategy_query.finish(msg)

    data = response.data
    img = data["url"]
    await strategy_query.finish(MessageSegment.image(img))


@update_query.handle(parameterless=[cold_down(name="更新公告", cd_time=0)])
async def _(event: GroupMessageEvent) -> NoReturn:
    """更新公告"""
    logger.info(f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 更新公告查询")
    url = "https://jx3.xoyo.com/launcher/update/latest.html"
    img = await browser.get_image_from_url(url=url, width=130, height=480)
    msg = MessageSegment.image(img)
    log = f"群{event.group_id} | 查询更新公告"
    logger.info(log)
    await update_query.finish(msg)


@saohua_query.handle(parameterless=[cold_down(name="骚话", cd_time=0)])
async def _(event: GroupMessageEvent) -> NoReturn:
    """骚话"""
    logger.info(f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 骚话 | 请求骚话")
    response = await api.data_chat_random()
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await saohua_query.finish(msg)

    data = response.data
    await saohua_query.finish(data["text"])


@sand_query.handle(parameterless=[cold_down(name="沙盘", cd_time=10)])
async def _(event: GroupMessageEvent, server: str = get_server()) -> NoReturn:
    """沙盘"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 沙盘查询 server：{server}"
    )
    response = await api.view_server_sand(server=server, robot='小猫饼', token=jx3api_v2_config.api_token)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await saohua_query.finish(msg)

    data = response.data
    url = data.get("url")
    await sand_query.finish(MessageSegment.image(url))


@price_query.handle(parameterless=[cold_down(name="物价查询", cd_time=10)])
async def _(event: GroupMessageEvent, name: str = get_value()) -> NoReturn:
    """物价查询"""
    logger.info(f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 物价查询 | 请求：{name}")
    if api.config.api_token:
        response = await api.data_trade_record(name=name)
    else:
        response = await api.data_trade_xiaohei(name=name)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await price_query.finish(msg)

    data = response.data
    pagename = "物品价格.html"
    item_name = data.get("name")
    item_info = data.get("desc")
    if api.config.api_token:
        item_img = data.get("view")
    else:
        item_img = data.get("upload")
    item_data = source.handle_data_price(data.get("data"))
    # xaxis_data = []
    # series_data = []
    # avg_price_30 = 0
    # follow_heat_30 = 0
    # max_price = 0
    # sell_cnt_30 = 0

    img = await browser.template_to_image(
        pagename=pagename,
        name=item_name,
        info=item_info,
        image=item_img,
        data=item_data,
    )
    await price_query.finish(MessageSegment.image(img))


@serendipity_query.handle(parameterless=[cold_down(name="角色奇遇", cd_time=10)])
async def _(
        event: GroupMessageEvent,
        server: str = get_server(),
        name: str = get_value(),
) -> NoReturn:
    """角色奇遇查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 角色奇遇查询 | 请求：server:{server},name:{name}"
    )

    ticket = await TicketInfo.get_ticket()
    response = await api.data_luck_serendipity(server=server, name=name, ticket=ticket)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await serendipity_query.finish(msg)

    data = response.data
    pagename = "角色奇遇.html"
    get_data = source.handle_data_serendipity(data)
    img = await browser.template_to_image(
        pagename=pagename, server=server, name=name, data=get_data
    )
    await serendipity_query.finish(MessageSegment.image(img))


@serendipity_list_query.handle(parameterless=[cold_down(name="奇遇统计", cd_time=10)])
async def _(
        event: GroupMessageEvent,
        server: str = get_server(),
        name: str = get_value(),
) -> NoReturn:
    """奇遇统计查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 奇遇统计查询 | 请求：server:{server},serendipity:{name}"
    )
    response = await api.view_luck_adventure(scale=2, server=server, name=name, robot='小猫饼',
                                             token=jx3api_v2_config.api_token)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await serendipity_list_query.finish(msg)

    await serendipity_list_query.finish(MessageSegment.image(response.data['url']))


@serendipity_summary_query.handle(parameterless=[cold_down(name="奇遇汇总", cd_time=10)])
async def _(event: GroupMessageEvent, server: str = get_server()) -> NoReturn:
    """奇遇汇总查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 奇遇汇总查询 | 请求：{server}"
    )
    response = await api.data_luck_collect(server=server)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await serendipity_summary_query.finish(msg)

    data = response.data
    pagename = "奇遇汇总.html"
    get_data = source.handle_data_serendipity_summary(data)
    img = await browser.template_to_image(
        pagename=pagename, server=server, data=get_data
    )
    await serendipity_summary_query.finish(MessageSegment.image(img))


@match_query.handle(parameterless=[cold_down(name="战绩查询", cd_time=10)])
async def _(
        event: GroupMessageEvent,
        server: str = get_server(),
        name: str = get_value(),
) -> NoReturn:
    """战绩查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 战绩查询 | 请求：server:{server},name:{name}"
    )
    ticket = await TicketInfo.get_ticket()
    response = await api.data_arena_recent(server=server, name=name, ticket=ticket)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await match_query.finish(msg)

    data = response.data
    pagename = "比赛记录.html"
    get_data = source.handle_data_match(data)
    img = await browser.template_to_image(
        pagename=pagename, server=server, name=name, data=get_data
    )
    await match_query.finish(MessageSegment.image(img))


@equip_query.handle(parameterless=[cold_down(name="装备属性", cd_time=10)])
async def _(
        event: GroupMessageEvent,
        server: str = get_server(),
        name: str = get_value(),
) -> NoReturn:
    """装备属性查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 装备属性查询 | 请求：server:{server},name:{name}"
    )
    ticket = await TicketInfo.get_ticket()
    response = await api.data_role_attribute(server=server, name=name, ticket=ticket)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await equip_query.finish(msg)

    data = response.data
    pagename = "角色装备.html"
    get_data = source.handle_data_equip(data)
    img = await browser.template_to_image(
        pagename=pagename, server=server, name=name, data=get_data
    )
    await equip_query.finish(MessageSegment.image(img))


@firework_query.handle(parameterless=[cold_down(name="烟花记录", cd_time=10)])
async def _(
        event: GroupMessageEvent,
        server: str = get_server(),
        name: str = get_value(),
) -> NoReturn:
    """烟花记录查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 烟花记录查询 | 请求：server:{server},name:{name}"
    )
    response = await api.data_look_firework(server=server, name=name)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await firework_query.finish(msg)

    data = response.data
    get_data = source.handle_data_firework(data)
    pagename = "烟花记录.html"
    img = await browser.template_to_image(
        pagename=pagename, server=server, name=name, data=get_data
    )
    await firework_query.finish(MessageSegment.image(img))


@recruit_query.handle(parameterless=[cold_down(name="招募查询", cd_time=10)])
async def _(
        event: GroupMessageEvent,
        server: str = get_server_with_keyword(),
        keyword: Optional[str] = get_keyword(),
) -> NoReturn:
    """招募查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 招募查询 | 请求：server:{server},keyword:{keyword}"
    )
    response = await api.view_member_recruit(server=server, keyword=keyword, robot='小猫饼',
                                             token=jx3api_v2_config.api_token)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await saohua_query.finish(msg)

    data = response.data
    url = data.get("url")
    await sand_query.finish(MessageSegment.image(url))


@zili_query.handle(parameterless=[cold_down(name="资历排行", cd_time=10)])
async def _(
        event: GroupMessageEvent,
        server: str = get_server_with_keyword(),
        kungfu: Optional[str] = get_keyword(),
) -> NoReturn:
    """资历榜"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 资历排行 | 请求：server:{server},kunfu:{kungfu}"
    )
    ticket = await TicketInfo.get_ticket()
    if not kungfu:
        kungfu = "ALL"
    response = await api.data_school_seniority(
        server=server, school=kungfu, ticket=ticket
    )
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await zili_query.finish(msg)

    data = response.data
    pagename = "资历排行.html"
    img = await browser.template_to_image(
        pagename=pagename,
        server=server,
        data=data,
    )
    await zili_query.finish(MessageSegment.image(img))


@shengwang_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
@laojianghu_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
@bingjia_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
@mingshi_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
@zhanjie_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
@xinhuo_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
@zixing_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
        server: str = get_server(),
        type_: str = get_type(),
        tittle: str = get_tittle(),
) -> NoReturn:
    """个人排名查询"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | {type_} | 请求：server:{server}"
    )
    response = await api.data_rank_various(server=server, type=type_)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await matcher.finish(msg)

    data = response.data
    for one in data:
        one["score"] = "{:,}".format(one["score"])
    pagename = "个人排行.html"
    img = await browser.template_to_image(
        pagename=pagename, server=server, type=type_, tittle=tittle, data=data
    )
    await matcher.finish(MessageSegment.image(img))


@aixin_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
@shenbing_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
        server: str = get_server(),
        type_: str = get_type(),
        tittle: str = get_tittle(),
        camp: str = get_camp(),
) -> NoReturn:
    """帮会排名"""
    type_ = camp + type_
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | {type_} | 请求：server:{server}"
    )
    response = await api.data_rank_tribe(server=server, type=type_)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await matcher.finish(msg)

    data = response.data
    for one in data:
        one["score"] = "{:,}".format(one["score"])
    pagename = "帮会排行.html"
    img = await browser.template_to_image(
        pagename=pagename, server=server, type=type_, tittle=tittle, data=data
    )
    await matcher.finish(MessageSegment.image(img))


@shilian_query.handle(parameterless=[cold_down(name="排行榜", cd_time=10)])
async def _(
        event: GroupMessageEvent,
        server: str = get_server(),
        school: str = get_value(),
) -> NoReturn:
    """试炼之地排行"""
    logger.info(
        f"<y>群{event.group_id}</y> | <g>{event.user_id}</g> | 试炼之地排行 | 请求：server:{server}，school:{school}"
    )
    response = await api.data_rank_trials(server=server, school=school)
    if response.code != 200:
        msg = f"查询失败，{response.msg}"
        await shilian_query.finish(msg)

    data = response.data
    for one in data:
        one["total"] = "{:,}".format(one["total"])
        one["score"] = "{:,}".format(one["score"])
    pagename = "试炼排行.html"
    img = await browser.template_to_image(
        pagename=pagename, server=server, school=school, data=data
    )
    await shilian_query.finish(MessageSegment.image(img))


@help.handle()
async def _(event: GroupMessageEvent) -> NoReturn:
    """帮助"""
    flag = bool(api.config.api_token)
    pagename = "查询帮助.html"
    img = await browser.template_to_image(pagename=pagename, flag=flag)
    await help.finish(MessageSegment.image(img))
