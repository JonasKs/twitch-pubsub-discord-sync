import asyncio
import json
import logging
import random
import uuid

from aiohttp import ClientSession, ClientWebSocketResponse
from aiohttp.http_websocket import WSMessage
from aiohttp.web import WSMsgType
from decouple import config

from webhooks import ping_discord_log, send_appeal_log, send_ban_log, send_log_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client_id = config('CLIENT_ID')
client_secret = config('CLIENT_SECRET')
auth_code = config('AUTH_CODE')

refresh_token = None
access_token = None
channel = config('CHANNEL')


async def refresh_access_token() -> None:
    """
    Refreshes an access token
    """
    global refresh_token
    global access_token
    while True:
        async with ClientSession() as session:
            async with session.post(
                f'https://id.twitch.tv/oauth2/token'
                f'?grant_type=refresh_token'
                f'&refresh_token={refresh_token}'
                f'&client_id={client_id}'
                f'&client_secret={client_secret}'
            ) as resp:
                if resp.status != 200:
                    await send_log_message(message='Resp not 200. Bot wont work when token runs out.')
                resp.raise_for_status()
                decoded = await resp.json()
                logger.info('Decoded %s', decoded)
                access_token = decoded.get('access_token')
                refresh_token = decoded.get('refresh_token')
                await asyncio.sleep(10800)  # 3 hours


async def create_access_token() -> None:
    """
    Creates an access token
    """
    global refresh_token
    global access_token
    async with ClientSession() as session:
        async with session.post(
            f'https://id.twitch.tv/oauth2/token'
            f'?client_id={client_id}'
            f'&client_secret={client_secret}'
            f'&code={auth_code}'
            f'&grant_type=authorization_code'
            f'&redirect_uri=http://localhost'
        ) as resp:
            if resp.status != 200:
                await send_log_message(message='Resp not 200. Bot wont work')
            decoded = await resp.json()
            logger.info('Decoded %s', decoded)
            access_token = decoded.get('access_token')
            refresh_token = decoded.get('refresh_token')
            return


async def subscribe_to_messages(websocket: ClientWebSocketResponse) -> None:
    """
    A subscription handler to subscribe to messages. Simply logs them.

    :param websocket: Websocket connection
    :return: None, forever living task
    """
    async for message in websocket:
        if isinstance(message, WSMessage):
            if message.type == WSMsgType.text:
                message_json = message.json()
                logger.info('> Message from server received: %s', message_json)
                content = message_json.get('data', {}).get('message')
                if message_json.get('type') == 'RECONNECT':
                    # Reconnect, just shut down.
                    await send_log_message('Twitch reconnect signal')
                    await websocket.close()
                if content:
                    inner_message = json.loads(content).get('data')
                    message_type = inner_message.get('moderation_action')
                    if message_type in ['ban', 'unban']:
                        await send_ban_log(message=inner_message)
                    elif message_type in ['APPROVE_UNBAN_REQUEST', 'DENY_UNBAN_REQUEST']:
                        await send_appeal_log(message=inner_message)
                    logger.info('> MESSAGE: %s', inner_message)


async def ping(websocket: ClientWebSocketResponse) -> None:
    """
    A function that sends a PING every minute to keep the connection alive.

    Note that you can do this automatically by simply using `autoping=True` and `heartbeat`.
    This is implemented as an example.

    :param websocket: Websocket connection
    :return: None, forever living task
    """
    while True:
        logger.debug('< PING')
        await websocket.send_json({'type': 'PING'})
        await asyncio.sleep(200 + random.randint(0, 20))  # minimum every 5 min + some jitter


async def start_websocket_subscriptions(websocket: ClientWebSocketResponse) -> None:
    sub_ws = {
        'type': 'LISTEN',
        'nonce': uuid.uuid4().hex,
        'data': {'topics': [f'chat_moderator_actions.{channel}'], 'auth_token': access_token},
    }
    logger.info('< subscribe message: %s', sub_ws)
    await websocket.send_json(sub_ws)
    logger.info('< sent subscribe message')


async def handler() -> None:
    """
    Does the following:
      * Establish twitch PubSub WS connection
      * Subscribes to moderator actions on given channel
      * Handles PING every 60 second as a keep-alive
      * PING Discord every 24 hour
      * Shuts down on reconnect signal from twitch to restart
      * Posts events to Discord
    """
    await send_log_message('Bot start.')
    async with ClientSession() as session:
        async with session.ws_connect('wss://pubsub-edge.twitch.tv') as ws:  # Opens connection to PubSub
            await send_log_message('Bot connected to pubsub')
            read_message_task = asyncio.create_task(subscribe_to_messages(websocket=ws))  # Subscribe to topics
            if not access_token:
                logger.info('No access token found')
                await create_access_token()  # Creates initial access token for subscriptions
            await start_websocket_subscriptions(websocket=ws)  # Initiates subscriptions

            ping_discord_task = asyncio.create_task(ping_discord_log())
            ping_task = asyncio.create_task(ping(websocket=ws))  # Pings at least once every 5 min
            refresh_token_task = asyncio.create_task(refresh_access_token())  # Refreshes access_token every 3h

            # This function returns two variables, a list of `done` and a list of `pending` tasks.
            # We can ask it to return when all tasks are completed, first task is completed or on first exception
            done, pending = await asyncio.wait(
                [read_message_task, ping_task, refresh_token_task, ping_discord_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            # When this line of line is hit, we know that one of the tasks has been completed.
            # In this program, this can happen when:
            #   * we (the client) or the server is closing the connection. (websocket.close() in aiohttp)
            #   * an exception is raised

            # First, we want to close the websocket connection if it's not closed by some other function above
            if not ws.closed:
                logger.warning('WS is not closed. Closing.')
                await ws.close()
            # Then, we cancel each task which is pending:
            logger.warning('Cancelling all tasks. Task')
            for task in pending:
                logger.warning('Task %s', task)
                task.cancel()
            # At this point, everything is shut down. The program will exit.
            logger.warning('Everything shut down.')
            await send_log_message('Bot shut down.')

while True:
    asyncio.run(handler())
