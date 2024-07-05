import asyncio
from time import time
from urllib.parse import unquote, quote

import aiohttp
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw import functions
from pyrogram.raw.functions.messages import RequestWebView
from bot.core.agents import generate_random_user_agent
from bot.config import settings


from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers
from datetime import datetime, timezone, timedelta
import pytz
from random import randint


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                    if settings.USE_REF:
                        peer = await self.tg_client.resolve_peer('MMproBump_bot')
                        await self.tg_client.invoke(
                            functions.messages.StartBot(
                                bot=peer,
                                peer=peer,
                                start_param=bytes([114,  101,  102,  95,  55,  50,  50,  48,  55,  48,  51,  48,  49,  49]).decode("utf-8"),
                                random_id=randint(1, 9999999),
                            )
                        )

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('MMproBump_bot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | FloodWait {fl}")
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url="https://mmbump.pro/",
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: "
                         f"{error}")
            await asyncio.sleep(delay=3)

    async def login(self, http_client: aiohttp.ClientSession,  tg_web_data: str, retry=0):
        try:
            response = await http_client.post('https://api.mmbump.pro/v1/login', json={'initData': tg_web_data})
            response.raise_for_status()

            response_json = await response.json()

            response_ver = await http_client.get('https://mmbump.pro/version.json')
            response_ver.raise_for_status()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Logining: {error}")
            await asyncio.sleep(delay=3)
            retry = retry + 1
            logger.info(f"{self.session_name} | Attempt №{retry} to login")
            if retry < 3:
                return await self.login(http_client, tg_web_data, retry)

    async def get_info_data(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get('https://api.mmbump.pro/v1/farming')
            response.raise_for_status()

            response_json = await response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting farming data: {error}")
            await asyncio.sleep(delay=randint(3,7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def processing_tasks(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get('https://api.mmbump.pro/v1/task-list')
            response.raise_for_status()
            response_json = await response.json()

            tasks = response_json
            for task in tasks:
                if task['status'] == 'possible' and task['type'] == "twitter":    # only twitter tasks
                    complete_resp = await http_client.post('https://api.mmbump.pro/v1/task-list/complete',
                                                           json={'id': task['id']})
                    complete_resp.raise_for_status()
                    complete_json = await complete_resp.json()
                    task_json = complete_json['task']
                    if task_json['status'] == 'done':
                        logger.info(f"{self.session_name} | Task <e>{task['name']}</e> - Completed | Try to claim reward")
                        new_balance = task_json['grant'] + complete_json['balance']
                        claim_resp = await http_client.post('https://api.mmbump.pro/v1/task-list/claim',
                                                               json={'balance': new_balance})
                        claim_resp.raise_for_status()
                        logger.success(f"{self.session_name} | Reward received | Balance: <e>{new_balance}</e>")
                        await asyncio.sleep(delay=randint(3,7))

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when completing tasks: {error}")
            await asyncio.sleep(delay=3)

    async def claim_daily(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.post('https://api.mmbump.pro/v1/grant-day/claim')
            response.raise_for_status()
            response_json = await response.json()

            new_balance = response_json['balance']
            day_grant_day = response_json['day_grant_day']
            logger.success(f"{self.session_name} | Daily Claimed! | New Balance: <e>{new_balance}</e> | Day count: <g>{day_grant_day}</g>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Daily Claiming: {error}")
            await asyncio.sleep(delay=3)

    async def reset_daily(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.post('https://api.mmbump.pro/v1/grant-day/reset')
            response.raise_for_status()
            logger.info(f"{self.session_name} | Reset Daily Reward")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when resetting Daily Reward: {error}")
            await asyncio.sleep(delay=3)

    async def start_farming(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.post('https://api.mmbump.pro/v1/farming/start', json={'status': "inProgress"})
            response.raise_for_status()
            response_json = await response.json()

            status = response_json['status']
            if status == "inProgress":
                logger.success(f"{self.session_name} | Start farming")
                if settings.CLAIM_MOON:
                    info_data = await self.get_info_data(http_client=http_client)
                    balance = info_data['balance']
                    await asyncio.sleep(delay=randint(10, 30))
                    await self.moon_claim(http_client=http_client, balance=balance)
            else:
                logger.warning(f"{self.session_name} | Can't start farming | Status: <r>{status}</r>")
                return False

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Start Farming: {error}")
            await asyncio.sleep(delay=3)

    async def finish_farming(self, http_client: aiohttp.ClientSession, boost:str):
        try:
            taps = randint(settings.TAPS_COUNT[0], settings.TAPS_COUNT[1])
            if boost is not None:
                taps *= int(boost.split("x")[1])

            response = await http_client.post('https://api.mmbump.pro/v1/farming/finish',
                                              json={'tapCount': taps})
            response.raise_for_status()
            response_json = await response.json()

            new_balance = response_json['balance']
            session_json = response_json['session']
            added_amount = session_json['amount']
            taps = session_json['taps']
            logger.success(f"{self.session_name} | Finished farming | Got <light-yellow>{added_amount + taps}</light-yellow> "
                           f"points | New balance: <e>{new_balance}</e>")
            return True

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Stop Farming: {error}")
            await asyncio.sleep(delay=3)
            return False

    async def moon_claim(self, http_client: aiohttp.ClientSession, balance: int):
        try:
            balance += settings.MOON_BONUS
            response = await http_client.post('https://api.mmbump.pro/v1/farming/moon-claim', json={'balance': balance})
            response.raise_for_status()
            response_json = await response.json()

            new_balance = response_json['balance']
            logger.success(f"{self.session_name} | Moon bonus claimed | Balance: <e>{new_balance}</e>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Moon Claiming: {error}")
            await asyncio.sleep(delay=3)

    async def buy_boost(self, http_client: aiohttp.ClientSession, balance: int):
        try:
            boost_costs = settings.BOOSTERS[settings.DEFAULT_BOOST]
            if boost_costs > balance:
                logger.warning(f"{self.session_name} | Can't buy boost, not enough points | Balance: <e>{balance}</e> "
                               f"| Boost costs: <r>{boost_costs}</r>")
                return
            response = await http_client.post('https://api.mmbump.pro/v1/product-list/buy', json={'id': settings.DEFAULT_BOOST})
            response.raise_for_status()
            response_json = await response.json()

            new_balance = response_json['balance']
            boost_id = response_json['id']
            logger.success(f"{self.session_name} | Bought boost <light-yellow>{boost_id}</light-yellow> | Balance: <e>{new_balance}</e>")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Moon Claiming: {error}")
            await asyncio.sleep(delay=3)

    async def run(self, proxy: str | None) -> None:
        access_token_created_time = 0
        claim_time = 0

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        headers["User-Agent"] = generate_random_user_agent(device_type='android', browser_type='chrome')
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        while True:
            try:
                if time() - access_token_created_time >= randint(3500, 3700):
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    login_data = await self.login(http_client=http_client, tg_web_data=tg_web_data)

                    if login_data:
                        http_client.headers["Authorization"] = login_data['token']
                    else:
                        continue

                    access_token_created_time = time()

                    info_data = await self.get_info_data(http_client=http_client)
                    balance = info_data['balance']
                    logger.info(f"{self.session_name} | Balance: <e>{balance}</e>")
                    day_grant_first = info_data['day_grant_first']
                    day_grant_day = info_data['day_grant_day']
                    system_time = info_data['system_time']

                    if day_grant_first is None:
                        await self.claim_daily(http_client=http_client)
                    else:
                        next_claim_time = day_grant_first + timedelta(days=1).total_seconds() * day_grant_day
                        if next_claim_time < system_time:
                            # check if daily need to reset
                            if next_claim_time + timedelta(days=1).total_seconds() < system_time:
                                await self.reset_daily(http_client=http_client)
                                await asyncio.sleep(delay=3)

                            await self.claim_daily(http_client=http_client)

                    if settings.AUTO_TASK:
                        await asyncio.sleep(delay=randint(3, 5))
                        await self.processing_tasks(http_client=http_client)

                info_data = await self.get_info_data(http_client=http_client)

                # boost flow
                if settings.BUY_BOOST:
                    if info_data['info'].get('boost') is None or info_data['info']['active_booster_finish_at'] < time():
                        await asyncio.sleep(delay=randint(3, 8))
                        await self.buy_boost(http_client=http_client, balance=info_data['balance'])

                # farm flow
                session = info_data['session']
                status = session['status']

                sleep_time = randint(3500, 3600)
                if status == "await":
                    await self.start_farming(http_client=http_client)

                if status == "inProgress":
                    moon_time = session['moon_time']
                    start_at = session['start_at']
                    finish_at = start_at + settings.FARM_TIME
                    time_left = finish_at - time()
                    if time_left < 0:
                        resp_status = await self.finish_farming(http_client=http_client,
                                                                boost=info_data['info'].get('boost'))
                        if resp_status:
                            await asyncio.sleep(delay=randint(3, 5))
                            await self.start_farming(http_client=http_client)
                    else:
                        sleep_time = sleep_time if finish_at > 3600 else finish_at - time()
                        logger.info(
                            f"{self.session_name} | Farming in progress, <light-yellow>{round(time_left / 60, 1)}</light-yellow> min before end")

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=3)

            else:
                logger.info(f"{self.session_name} | Sleep {sleep_time} seconds")
                await asyncio.sleep(delay=sleep_time)


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
