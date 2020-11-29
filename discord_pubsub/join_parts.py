import asyncio
import logging

from aiohttp import ClientSession

from discord_pubsub.webhooks import send_join_part_message, send_log_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def compare_join_parts():
    last_viewers = []
    while True:
        async with ClientSession() as session:
            async with session.get('https://tmi.twitch.tv/group/user/therunningmanz/chatters') as response:
                if response.status != 200:
                    await send_log_message(message='Unable to fetch join/parts.')
                    await asyncio.sleep(20)
                else:
                    json_resp = await response.json()
                    current_viewers = json_resp.get('chatters', {}).get('viewers', [])
                    logger.info('Current viewers: %s', current_viewers)
                    if not last_viewers:
                        logger.info('No last viewers')
                        last_viewers = current_viewers
                    else:
                        joins = [user for user in current_viewers if user not in last_viewers]
                        parts = [user for user in last_viewers if user not in current_viewers]
                        last_viewers = current_viewers
                        logger.info('Joins %s', joins)
                        logger.info('Parts %s', parts)
                        await send_join_part_message(joins=joins, parts=parts)
        await asyncio.sleep(120)  # 120 sec interval
