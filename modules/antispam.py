import asyncio
import io
import sys
import textwrap
import traceback
from contextlib import redirect_stderr, redirect_stdout
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple
import nextcord
from nextcord.ext import commands
from datetime import timedelta
from colorama import Fore

sc = 0x00de00	

class ESpamLevel(IntEnum):
    NormalLv1 = 6
    NormalLv2 = 10
    NormalLv3 = 15
    MultiChannelLv1 = 3
    MultiChannelLv2 = 5
    MultiChannelLv3 = 8

SPAM_TIMEOUT = 15
MULTI_CHANNEL_FLAG = 3
messages: Dict[int, List[Tuple[nextcord.Message, asyncio.events.TimerHandle]]] = {}
detected: Dict[int, ESpamLevel] = {}
Nolist = [4566667666]

def format_exception(exc: Exception) -> str:
    return ''.join(list(traceback.TracebackException.from_exception(exc).format()))

def cleanup_code(content: str) -> str:
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip(' \n')

async def aexec(body: str, variables: dict) -> Tuple[Any, str, str]:
    body = cleanup_code(body)
    stdout = io.StringIO()
    stderr = io.StringIO()

    exc = f'async def __exc__():\n{textwrap.indent(body, "  ")}'
    exec(exc, variables)

    func = variables['__exc__']
    with redirect_stdout(stdout), redirect_stderr(stderr):
        return await func(), stdout.getvalue(), stderr.getvalue()

async def delete_messages(channel: nextcord.TextChannel, messages: List[nextcord.Message]) -> None:
    for m in [messages[i:i+100] for i in range(0, len(messages), 100)]:
        await channel.delete_messages(m)

async def delete_all(messages: List[nextcord.TextChannel]):
    mes = {}
    for m in messages:
        if m.channel not in mes:
            mes[m.channel] = []
        mes[m.channel].append(m)
    for c, ms in mes.values():
        await delete_messages(c, ms)

async def soft_ban(member: nextcord.Member, delete_message_days: int = 1):
    await member.ban(reason='ソフトバン', delete_message_days=delete_message_days)
    await member.unban(reason='ソフトバン')

async def spam_check(self,message: nextcord.Message) -> None:
    if message.author.bot or message.guild is None or not isinstance(message.author, nextcord.Member):
        return False
    if (message.author.guild_permissions.administrator or message.author.guild_permissions.manage_messages):
        return False

    def callback(message):
        def inner():
            messages[message.author.id].remove(
                nextcord.utils.find(lambda pair: pair[0] is message, messages[message.author.id])
            )
            if len(messages[message.author.id]) == 0 and message.author.id in detected:
                detected.pop(message.author.id)
        
        return inner

    if message.author.id not in messages:
        messages[message.author.id] = []
    messages[message.author.id].append((
        message,
        self.bot.loop.call_later(SPAM_TIMEOUT, callback(message))
    ))
    message_count = len(messages[message.author.id])

    level: Optional[ESpamLevel] = None
    channels = tuple(map(lambda pair: pair[0].channel, messages[message.author.id]))
    if (message_count >= ESpamLevel.MultiChannelLv1
            and len(set(channels)) >= MULTI_CHANNEL_FLAG):
        levels = (ESpamLevel.MultiChannelLv3, ESpamLevel.MultiChannelLv2, ESpamLevel.MultiChannelLv1)
        for lv in levels:
            if message_count >= lv:
                level = lv
                break
    elif (message_count >= ESpamLevel.NormalLv1):
        levels = (ESpamLevel.NormalLv3, ESpamLevel.NormalLv2, ESpamLevel.NormalLv1)
        for lv in levels:
            if message_count >= lv:
                level = lv
                break

    if level is not None:
        for count, (m, timer) in enumerate(messages[message.author.id]):
            timer.cancel()
            messages[m.author.id][count] = (
                m,
                self.bot.loop.call_later(SPAM_TIMEOUT, callback(m))
            )

        detected_level = detected.get(message.author.id)
        if (detected_level is None
                or detected_level in (ESpamLevel.NormalLv3, ESpamLevel.MultiChannelLv3)
                or detected_level is not level):
            detected[message.author.id] = level
            if level in (ESpamLevel.NormalLv1, ESpamLevel.MultiChannelLv1):
                embed=nextcord.Embed(description=f"警告\n{message.author.mention}スパムをやめてください",color=0XFF00FF)
                await message.channel.send(embed=embed, delete_after = 10)
                async def task():
                    await asyncio.sleep(10)
                    try:
                      await delete_all(messages[message.channel.id])
                    except:
                      pass
                self.bot.loop.create_task(task())
            elif level in (ESpamLevel.NormalLv2, ESpamLevel.MultiChannelLv2):
                try:
                    await delete_messages(message.channel, tuple(map(lambda pair: pair[0], messages[message.author.id])))
                except Exception as e:
                    print(format_exception(e), file=sys.stderr)
                embed=nextcord.Embed(description=f"最終警告\n{message.author.mention}スパムをやめてください\nもしスパムの意図がないのであれば、{SPAM_TIMEOUT + 3}秒間はチャットをしないで下さい",color=0xff0000)
                await message.channel.send(embed=embed, delete_after = 10)		

                async def task():
                    await asyncio.sleep(10)
                    try:
                      await delete_all(messages[message.channel.id])
                    except:
                      pass

                self.bot.loop.create_task(task())
            else:
                try:
                    await message.author.timeout(timedelta(minutes = 10), reason = "Spamming")
                except Exception as e:
                    print(format_exception(e), file=sys.stderr)
                    embed=nextcord.Embed(description=f"{message.author.mention}のタイムアウトに失敗しました",color=0xff0000)
                    await message.channel.send(embed=embed)	
                    async def task():
                        await asyncio.sleep(10)
                        await delete_all(messages[message.channel.id])

                    self.bot.loop.create_task(task())
                else:
                    embed=nextcord.Embed(description=f"{message.author.mention}をスパムでタイムアウトしました",color=0xff0000)
                    await message.channel.send(embed=embed)
                try:
                    await delete_messages(message.channel, tuple(map(lambda pair: pair[0], messages[message.author.id])))
                except Exception as e:
                    print(format_exception(e), file=sys.stderr)
                return False

class antispam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
      print(Fore.BLUE + "|antispam      |" + Fore.RESET)

    @commands.Cog.listener()
    async def on_message(self,message:nextcord.Message):
      if message.author.id in Nolist:
        return
      if await spam_check(self,message):
        return
      if message.author.bot:
        return
			         
def setup(bot):
    return bot.add_cog(antispam(bot))