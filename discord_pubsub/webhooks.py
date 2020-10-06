import asyncio
import logging

from aiohttp import ClientSession
from decouple import config
from discord import AsyncWebhookAdapter, Embed, Webhook

logger = logging.getLogger(__name__)


async def send_ban_log(message: dict) -> None:
    """
    Sends a ban or unban log to Discord
    :param message: Message dict recieved by the Twitch PubSub websocket
        {
          "type": "chat_login_moderation",
          "moderation_action": "ban",
          "args": [
            "hotfix_is_a_bot",
            ""
          ],
          "created_by": "hotfixguru",
          "created_by_user_id": "32257034",
          "msg_id": "",
          "target_user_id": "137335436",
          "target_user_login": "",
          "from_automod": false
        }
    """
    logger.debug('Sending ban log webhook entry')
    ban_type = message.get('moderation_action')
    color = 0xFF0000 if ban_type == 'ban' else 0x00FF00
    async with ClientSession() as session:
        webhook = Webhook.from_url(config('BAN_WEBHOOK_URL'), adapter=AsyncWebhookAdapter(session))
        embed = Embed(title=f'New {ban_type}', color=color)
        embed.add_field(
            name=f'{ban_type.capitalize()}ned user',
            value=f'{message.get("args")[0]} (ID: {message.get("target_user_id")})',
            inline=True,
        )
        embed.add_field(name=f'{ban_type.capitalize()} by', value=message.get('created_by'), inline=True)
        await webhook.send(embed=embed)
    return


async def send_appeal_log(message: dict) -> None:
    """
    Sends an appeal action to Discord

    :param message:
        {
          'moderation_action': 'DENY_UNBAN_REQUEST',
          'created_by_id': '32257034',
          'created_by_login': 'hotfixguru',
          'moderator_message': 'test unban reason',
          'target_user_id': '137335436',
          'target_user_login': 'hotfix_is_a_bot'
        }
    """
    logger.debug('Sending ban log webhook entry')
    ban_type = message.get('moderation_action')
    action = 'New appeal denied' if ban_type == 'DENY_UNBAN_REQUEST' else 'New appeal approved'
    color = 0xFF0000 if ban_type == 'DENY_UNBAN_REQUEST' else 0x00FF00
    async with ClientSession() as session:
        webhook = Webhook.from_url(config('APPEAL_WEBHOOK_URL'), adapter=AsyncWebhookAdapter(session))
        embed = Embed(title=action, color=color)
        embed.add_field(
            name='Target user',
            value=f'{message.get("target_user_login")} (ID: {message.get("target_user_id")})',
            inline=True,
        )
        embed.add_field(name=f'Request handled by', value=message.get('created_by_login'), inline=True)
        embed.add_field(name=f'Moderator message', value=message.get('moderator_message', 'No message'), inline=False)
        await webhook.send(embed=embed)
    return


async def send_log_message(message: str) -> None:
    logger.info('Sending log message %s', message)
    async with ClientSession() as session:
        webhook = Webhook.from_url(config('LOG_WEBHOOK_URL'), adapter=AsyncWebhookAdapter(session))
        embed = Embed(title='Log', color=0x000000)
        embed.add_field(name=f'Message', value=message, inline=False)
        await webhook.send(embed=embed)
    return


async def ping_discord_log():
    while True:
        await send_log_message(message='PING')
        await asyncio.sleep(86400)  # Sleep 24h
