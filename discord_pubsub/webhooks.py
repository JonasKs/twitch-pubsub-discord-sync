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
        if len(list(filter(None, message.get("args")))) > 1:  # Reason is an empty string if not provided
            embed.add_field(
                name=f'Ban reason',
                value=' '.join(message.get("args")[1:]),  # Skip username
                inline=False,
            )
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


async def send_join_part_message(joins: list, parts: list) -> None:
    """
    Log who's joining the chat and who's left chat.
    :param joins: People who joined
    :param parts: People who left
    """

    logger.info('Sending join/part message. Join %s, parts %s', joins, parts)
    # Each value can be 1024 chars, each embed can be 2048
    async with ClientSession() as session:
        if joins and len(joins) <= 240:
            logger.info('Joins limit accepted')
            card_chunks = [joins[x:x+80] for x in range(0, len(joins), 80)]  # 80 names pr embed
            for card in card_chunks:
                logger.info('Card %s', card)
                join = Webhook.from_url(config('JOIN_PART_WEBHOOK_URL'), adapter=AsyncWebhookAdapter(session))
                join_chunks = [card[x:x+40] for x in range(0, len(card), 40)]  # max 40 names pr. value
                embed_join = Embed(title='Joins', color=0x00FF00)
                for chunk in join_chunks:
                    embed_join.add_field(name=f'Joins', value=f"``` {','.join(chunk)} ```", inline=False)
                    logger.info('Join chunk: %s', chunk)
                await join.send(embed=embed_join)

        if parts and len(joins) <= 240:
            logger.info('Parts limit accepted')
            card_chunks = [parts[x:x+80] for x in range(0, len(parts), 80)]  # 80 names pr embed
            for card in card_chunks:
                logger.info('Card %s', card)
                part = Webhook.from_url(config('JOIN_PART_WEBHOOK_URL'), adapter=AsyncWebhookAdapter(session))
                embed_part = Embed(title='Parts', color=0xFF0000)
                part_chunks = [card[x:x+40] for x in range(0, len(card), 40)]
                for chunk in part_chunks:
                    embed_part.add_field(name=f'Parts', value=f"``` {','.join(chunk)} ```", inline=False)
                    logger.info('Part chunk: %s', chunk)
                await part.send(embed=embed_part)
    return


async def rules() -> None:
    """
    Rules. Only used once, but I'll keep it in git since it's annoying to format if Paul ever want them changed.
    """
    async with ClientSession() as session:
        webhook = Webhook.from_url(config('RULES_WEBOOK_URL'), adapter=AsyncWebhookAdapter(session))
        embed = Embed(title="Welcome!", description="Please take a minute to read through these rules.")
        embed.set_author(
            name="TheRunningManZ",
            url="https://twitch.tv/therunningmanz",
            icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/3ce6ba9a-43cf-4611-8025-315a841cbeca-profile_image-300x300.png",
        )
        embed.set_thumbnail(url="https://legal-term.com/wp-content/uploads/2020/02/Laws-of-Achievement.jpg")
        embed.add_field(
            name="Rules",
            value="**1)** No discussion around Racism/sexism/homophobia/politics/Religion/Gun Laws please  \n"
            "**2)** Do not use words such as cancer, aids, autistic etc "
            "to describe something about a game or anything else. We don't do that here.  \n"
            "**3)** No self promotion or promoting friends. "
            "Sharing your videos/highlights in the your clips section is obviously fine!  \n"
            "**4)** Please don't ask for the server details that TRMZ is playing on. "
            "Giving out server details spoils the stream for all viewers.  \n"
            "**5)** Please refrain from discussing glitches or exploits in the game and explaining how to do them.  \n"
            "**6)** Any stream sniping or mentioning that you/your friends have stream sniped TRMZ, "
            "or are trying to, will result in a ban. Even joking about it!  \n"
            "**7)** A mods decision is final, persistent arguing over a decision will result in a permanent ban  \n"
            "**8)** Follow the [Discord Community Guidelines](https://discord.com/guidelines) "
            "and [Terms Of Service](https://discord.com/terms).",
            inline=False,
        )
        embed.add_field(
            name='DayZ server',
            value='**1)** Server rules be found [here](https://www.spaggie.com/server-rules/).  \n'
            '**2)** Please keep any discussion related to the servers in '
            '<#525680843406966799> and <#758383957657780285>  \n'
            '**3)** If you have met a cheater, experience lag or need assistance '
            'from an admin [use this form](https://www.spaggie.com/complaint/)',
        )
        embed.set_footer(
            text="If you have any questions or concerns, please do not hesitate contacting the moderators."
        )
        await webhook.send(embed=embed)

