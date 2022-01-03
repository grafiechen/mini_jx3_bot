from typing import Optional, Tuple

from httpx import AsyncClient
from src.utils.config import config
from src.utils.log import logger


class Weather(object):
    '''请求天气封装'''

    _api_key: str
    '''和风天气的apikey'''
    _weather_api: str
    '''api地址'''
    _geoapi: str
    '''请求城市id地址'''
    _weather_warning: str
    '''天气灾害预警地址'''
    _client: AsyncClient
    '''httpx异步客户端'''

    def __new__(cls, *args, **kwargs):
        '''单例'''
        if not hasattr(cls, '_instance'):
            orig = super(Weather, cls)
            cls._instance = orig.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self._api_key = config.weather['api_key']
        is_commercial = config.weather['commercial']
        if is_commercial:
            # 商业apikey
            self._weather_api = "https://api.qweather.com/v7/weather/"
            self._geoapi = "https://geoapi.qweather.com/v2/city/"
            self._weather_warning = "https://api.qweather.com/v7/warning/now"
        else:
            # 开发版apikey
            self._weather_api = "https://devapi.qweather.com/v7/weather/"
            self._geoapi = "https://geoapi.qweather.com/v2/city/"
            self._weather_warning = "https://devapi.qweather.com/v7/warning/now"
        self._client = AsyncClient()

    async def _get_city_info(self, city_kw: str, api_type: str = "lookup") -> Optional[Tuple[int, str]]:
        '''
        :说明
            获取城市信息

        :参数
            * city_kw：请求名称
            * api_type：请求方法，默认为“lookup”

        :返回
            * city_id：城市id
            * city_name：城市名
        '''
        url = self._geoapi+api_type
        params = {"location": city_kw, "key": self._api_key}
        try:
            req_json: dict = await self._client.get(url=url, params=params).json()
            code = req_json['code']
            city_id: int = req_json["location"][0]['id']
            city_name: str = req_json["location"][0]["name"]
            if code != 200:
                log = f"<r>获取城市id失败，code：{code}，请参考 https://dev.qweather.com/docs/start/status-code/</r>"
                logger.opt(colors=True).error(log)
                return None
            return city_id, city_name

        except Exception as e:
            log = f"<r>获取城市id接口失败：{str(e)}</r>"
            logger.opt(colors=True).error(log)
            return None

    async def _get_weather_info(self, api_type: str, city_id: str) -> Optional[dict]:
        '''
        :说明
            获取城市天气信息

        :参数
            * api_type：请求方式
            * city_id：城市id

        :返回
            * dict：返回数据
        '''
        url = self._weather_api+api_type
        params = {"location": city_id, "key": self._api_key}
        try:
            req_json = await self._client.get(url=url, params=params).json()
            code = req_json['code']
            if code != 200:
                log = f"<r>获取天气消息失败，code：{code}，请参考 https://dev.qweather.com/docs/start/status-code/</r>"
                logger.opt(colors=True).error(log)
                return None
            return req_json
        except Exception as e:
            log = f"<r>访问天气接口失败：{str(e)}</r>"
            logger.opt(colors=True).error(log)
            return None

    async def _get_weather_warning(self, city_id: str) -> Optional[dict]:
        '''
        :说明
            获取城市天气预警信息

        :参数
            * city_id：城市id

        :返回
            * dict：返回数据
        '''
        params = {"location": city_id, "key": self._api_key}
        try:
            req_json = await self._client.get(url=self._weather_warning, params=params).json()
            code = req_json['code']
            if code != 200:
                log = f"<r>获取天气预警失败，code：{code}，请参考 https://dev.qweather.com/docs/start/status-code/</r>"
                logger.opt(colors=True).error(log)
                return None
            return req_json

        except Exception as e:
            log = f"<r>访问天气预警接口失败：{str(e)}</r>"
            logger.opt(colors=True).error(log)
            return None

    async def get_weather(self, city: str) -> Optional[dict]:
        '''
        :说明
            获取城市天气

        :参数
            * city：城市名

        :返回
            * dict：天气数据字典
        '''
        city_id, city_name = await self._get_city_info(city)
        if not city_id:
            return None
        daily_info = await self._get_weather_info("7d", city_id)
        now_info = await self._get_weather_info("now", city_id)
        if not daily_info or not now_info:
            return None
        warning = await self._get_weather_warning(city_id)
        if not warning:
            return None
        daily = daily_info["daily"]
        now = now_info["now"]
        data = {
            "city": city_name,
            "now": now,
            "day1": daily[0],
            "day2": daily[1],
            "day3": daily[2],
            "day4": daily[3],
            "day5": daily[4],
            "day6": daily[5],
            "day7": daily[6],
            "warning": warning
        }
        return data


weather_client = Weather()
'''天气请求客户端'''