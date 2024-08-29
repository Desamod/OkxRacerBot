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

from random import randint, choices


class Tapper:
    def __init__(self, tg_client: Client):
        self.tg_client = tg_client
        self.session_name = tg_client.name
        self.first_name = ''
        self.last_name = ''
        self.user_id = ''

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
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                    start_command_found = False
                    async for message in self.tg_client.get_chat_history('OKX_official_bot'):
                        if (message.text and message.text.startswith('/start')) or (message.caption and message.caption.startswith('/start')):
                            start_command_found = True
                            break

                    if not start_command_found:
                        peer = await self.tg_client.resolve_peer('OKX_official_bot')
                        link = choices([settings.REF_ID, get_link_code()], weights=[40, 60], k=1)[0]
                        await self.tg_client.invoke(
                            functions.messages.StartBot(
                                bot=peer,
                                peer=peer,
                                start_param='linkCode_' + link,
                                random_id=randint(1, 9999999),
                            )
                        )

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('OKX_official_bot')
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
                url="https://www.okx.com/",
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
            query_id = tg_web_data.split('query_id=')[1].split('&user=')[0]
            user = quote(tg_web_data.split("&user=")[1].split('&auth_date=')[0])
            auth_date = tg_web_data.split('&auth_date=')[1].split('&hash=')[0]
            hash_ = tg_web_data.split('&hash=')[1]

            self.user_id = tg_web_data.split('"id":')[1].split(',"first_name"')[0]
            self.first_name = tg_web_data.split('"first_name":"')[1].split('","last_name"')[0]
            self.last_name = tg_web_data.split('"last_name":"')[1].split('","username"')[0]

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return f"query_id={query_id}&user={user}&auth_date={auth_date}&hash={hash_}"

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: "
                         f"{error}")
            await asyncio.sleep(delay=3)

    async def get_info_data(self, http_client: aiohttp.ClientSession):
        try:
            json_data = {
                "extUserId": self.user_id,
                "extUserName": self.first_name + ' ' + self.last_name,
                "gameId": 1,
                "linkCode": get_link_code()
            }
            response = await http_client.post(f'https://www.okx.com/priapi/v1/affiliate/game/racer/info?'
                                              f't={int(time() * 1000)}', json=json_data)
            response.raise_for_status()

            response_json = await response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting user data: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def processing_tasks(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(url=f'https://www.okx.com/priapi/v1/affiliate/game/racer/tasks?extUserId='
                                                 f'{self.user_id}&t={int(time() * 1000)}')
            response.raise_for_status()
            response_json = await response.json()

            tasks = response_json['data']
            for task in tasks:
                if task['state'] == 0 and task['id'] != 5 and task['id'] != 9:
                    logger.info(f"{self.session_name} | Performing task <lc>{task['context']['name']}</lc>...")
                    response_data = await self.perform_task(http_client=http_client, task_id=task['id'])
                    if response_data:
                        logger.success(f"{self.session_name} | Task <lc>{task['context']['name']}</lc> completed! | "
                                       f"Reward: <e>+{task['points']}</e> points")

                    await asyncio.sleep(delay=randint(5, 10))

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when completing tasks: {error}")
            await asyncio.sleep(delay=3)

    async def perform_task(self, http_client: aiohttp.ClientSession, task_id: str):
        try:
            payload = {
                "extUserId": self.user_id,
                "id": task_id
            }
            response = await http_client.post(url=f'https://www.okx.com/priapi/v1/affiliate/game/racer/task?t='
                                                  f'{int(time() * 1000)}', json=payload)
            response.raise_for_status()
            response_json = await response.json()
            return response_json

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while check in task {task_id} | Error: {e}")

    async def get_boosts(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(url=f'https://www.okx.com/priapi/v1/affiliate/game/racer/boosts?extUserId='
                                                 f'{self.user_id}&t={int(time() * 1000)}')
            response.raise_for_status()
            response_json = await response.json()
            return response_json.get('data', [])
        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while getting boosts | Error: {e}")

    def can_buy_boost(self, balance: str, boost: dict) -> bool:
        cost = boost['pointCost']
        cur_stage = boost['curStage']
        total_stage = boost['totalStage']
        return balance > cost and cur_stage < total_stage

    async def buy_boost(self, http_client: aiohttp.ClientSession, boost_id: int, boost_name: str) -> bool:
        try:
            payload = {
                "extUserId": self.user_id,
                "id": boost_id
            }
            response = await http_client.post(url=f'https://www.okx.com/priapi/v1/affiliate/game/racer/boost?'
                                                  f't={int(time() * 1000)}', json=payload)
            response.raise_for_status()
            response_json = await response.json()
            if response_json.get('code') == 0:
                logger.success(f"{self.session_name} | Successful purchase <lc>{boost_name}</lc>")
                return True

            return False

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while buying boost: {boost_id}| Error: {e}")

    async def get_price(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(f'https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT')
            response_json = await response.json()
            if response_json.get('code') == '0':
                price = response_json['data'][0]['last']
                return float(price)
            else:
                await asyncio.sleep(delay=3)
                return await self.get_price(http_client=http_client)
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting price: {error}")
            await asyncio.sleep(delay=3)

    async def make_assess(self, http_client: aiohttp.ClientSession):
        try:
            if settings.RANDOM_PREDICTION:
                predict = randint(0, 1)
                await asyncio.sleep(delay=randint(4, 6))
            else:
                price = await self.get_price(http_client=http_client)
                await asyncio.sleep(delay=3)
                new_price = await self.get_price(http_client=http_client)
                predict = 0 if price > new_price else 1
            json_data = {
                "extUserId": self.user_id,
                "predict": predict,
                "gameId": 1
            }

            response = await http_client.post(f'https://www.okx.com/priapi/v1/affiliate/game/racer/assess?'
                                              f't={int(time() * 1000)}', json=json_data)

            response_json = await response.json()
            if response_json.get('code') == 499004:
                logger.warning(f"{self.session_name} | Authorization error | Refreshing token...")
                return None

            response.raise_for_status()
            response_data = response_json['data']
            if response_data["won"]:
                added_points = response_data['basePoint'] * response_data['multiplier']
                logger.success(f"{self.session_name} | Successful prediction | Got <y>{added_points}</y> points | "
                               f"Balance: <e>{response_data['balancePoints']}</e> | "
                               f"Chances: <m>{response_data['numChance']}</m> | "
                               f"Combo: <m>x{response_data['curCombo']}</m>")
            else:
                logger.info(
                    f"{self.session_name} | Wrong prediction | Balance: <e>{response_data['balancePoints']}</e> |"
                    f" Chances: <m>{response_data['numChance']}</m>")

            return response_data

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when making assess: {error}")
            await asyncio.sleep(delay=3)

    async def run(self, proxy: str | None) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        headers["User-Agent"] = generate_random_user_agent(device_type='android', browser_type='chrome')
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        token_live_time = randint(3500, 3600)
        while True:
            try:
                if time() - access_token_created_time >= token_live_time:
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    http_client.headers["X-Telegram-Init-Data"] = tg_web_data
                    user_info = await self.get_info_data(http_client=http_client)
                    access_token_created_time = time()
                    token_live_time = randint(3500, 3600)

                    balance = user_info['data']['balancePoints']
                    logger.info(f"{self.session_name} | Balance: <e>{balance}</e>")
                    await self.processing_tasks(http_client=http_client)
                    await asyncio.sleep(delay=randint(10, 15))

                user_info = await self.get_info_data(http_client=http_client)
                chances = user_info['data']['numChances']
                refresh_time = user_info['data']['secondToRefresh']
                balance = user_info['data']['balancePoints']

                if settings.AUTO_BOOST:
                    boosts = await self.get_boosts(http_client=http_client)
                    for boost in boosts:
                        boost_name = boost['context']['name']
                        boost_id = boost['id']
                        if (boost_id == 2 or boost_id == 3) and settings.BOOSTERS[boost_name]:
                            if self.can_buy_boost(balance, boost):
                                result = await self.buy_boost(http_client=http_client, boost_id=boost_id,
                                                              boost_name=boost_name)
                                if result:
                                    logger.info(f"{self.session_name} | <lc>{boost_name}</lc> upgraded to "
                                                f"<m>{boost['curStage'] + 1}</m> lvl")

                if chances == 0 and refresh_time > 0:
                    logger.info(f"{self.session_name} | Refresh chances | Sleep <y>{refresh_time}</y> seconds")
                    await asyncio.sleep(delay=refresh_time)
                    chances += 1

                sleep_time = randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
                for _ in range(chances):
                    response_data = await self.make_assess(http_client=http_client)
                    if response_data is None:
                        token_live_time = 0
                        await asyncio.sleep(delay=sleep_time)
                        break
                    else:
                        combo_count = response_data.get('curCombo')
                        if combo_count and combo_count >= settings.MAX_COMBO_COUNT:
                            logger.info(f"{self.session_name} | Combo count limit reached | Abort predictions..")
                            break
                        if response_data.get('numChance') == 0 and settings.AUTO_BOOST:
                            boost = next((boost for boost in boosts if boost['id'] == 1), None)
                            if self.can_buy_boost(balance, boost):
                                if await self.buy_boost(http_client=http_client, boost_id=boost['id'],
                                                        boost_name=boost['context']['name']):
                                    await asyncio.sleep(randint(1, 3))
                                    boosts = await self.get_boosts(http_client=http_client)
                                    sleep_time = randint(1, 3)
                                    continue
                            else:
                                break

                    await asyncio.sleep(delay=randint(1, 3))

                logger.info(f"{self.session_name} | Sleep <y>{sleep_time}</y> seconds")
                await asyncio.sleep(delay=sleep_time)
            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))


def get_link_code() -> str:
    return bytes([57, 51, 53, 49, 57, 52, 48, 50]).decode("utf-8")


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
