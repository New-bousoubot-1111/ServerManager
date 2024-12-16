import asyncio
import sys
import traceback
from datetime import timedelta
from enum import IntEnum
from typing import Dict, List, Tuple
import nextcord
from nextcord.ext import commands
from colorama import Fore

SPAM_TIMEOUT = 15  # スパムメッセージの有効時間（秒）
DETECTION_LEVELS = [1, 2, 3, 4]  # 処罰段階を表すリスト
EXCLUDED_USERS = [800255014463078462]  # スパム検出対象外のユーザー

messages: Dict[int, List[nextcord.Message]] = {}  # ユーザーごとのメッセージ追跡
violations: Dict[int, int] = {}  # ユーザーごとのスパム違反回数


def format_exception(exc: Exception) -> str:
    """エラー内容をフォーマット"""
    return ''.join(traceback.TracebackException.from_exception(exc).format())


async def delete_messages(channel: nextcord.TextChannel, msgs: List[nextcord.Message]) -> None:
    """指定されたメッセージを削除"""
    for chunk in [msgs[i:i + 100] for i in range(0, len(msgs), 100)]:
        await channel.delete_messages(chunk)


async def handle_violation(bot: commands.Bot, message: nextcord.Message):
    """スパム検出時の処理"""
    user_id = message.author.id
    member = message.author
    channel = message.channel

    # ユーザーの違反回数を記録
    if user_id not in violations:
        violations[user_id] = 0
    violations[user_id] += 1
    level = violations[user_id]

    try:
        if level == 1:
            # 1回目の処罰：1時間のタイムアウト
            await member.timeout(timedelta(hours=1), reason="スパム行為 - 1回目")
            embed = nextcord.Embed(
                description=f"{member.mention} がスパム行為のため、1時間タイムアウトされました。",
                color=0xFFFF00,
            )
            await channel.send(embed=embed)

        elif level == 2:
            # 2回目の処罰：1日のタイムアウト
            await member.timeout(timedelta(days=1), reason="スパム行為 - 2回目")
            embed = nextcord.Embed(
                description=f"{member.mention} がスパム行為のため、1日タイムアウトされました。",
                color=0xFFA500,
            )
            await channel.send(embed=embed)

        elif level == 3:
            # 3回目の処罰：サーバーからのキック
            await member.kick(reason="スパム行為 - 3回目")
            embed = nextcord.Embed(
                description=f"{member.mention} がスパム行為のため、サーバーからキックされました。",
                color=0xFF4500,
            )
            await channel.send(embed=embed)

        elif level >= 4:
            # 4回目以降の処罰：サーバーからのバン
            await member.ban(reason="スパム行為 - 4回目以上")
            embed = nextcord.Embed(
                description=f"{member.mention} がスパム行為のため、サーバーからバンされました。",
                color=0xFF0000,
            )
            await channel.send(embed=embed)

    except Exception as e:
        # エラー発生時のログ出力
        print(format_exception(e), file=sys.stderr)


async def spam_check(bot: commands.Bot, message: nextcord.Message) -> None:
    """スパム行為を検出"""
    if message.author.bot or message.author.id in EXCLUDED_USERS:
        return

    user_id = message.author.id
    if user_id not in messages:
        messages[user_id] = []

    # メッセージを追跡リストに追加
    messages[user_id].append(message)

    # メッセージの有効期限を設定
    async def remove_message():
        if user_id in messages:
            messages[user_id] = [msg for msg in messages[user_id] if msg.id != message.id]

    bot.loop.call_later(SPAM_TIMEOUT, asyncio.create_task, remove_message())

    # スパムとみなす閾値を超えたか判定
    if len(messages[user_id]) > 5:  # 例: 5メッセージ以上送信するとスパム
        await handle_violation(bot, message)
        await delete_messages(message.channel, messages[user_id])
        messages[user_id].clear()  # スパム検出後、メッセージリストをクリア


class antiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|antispam      |" + Fore.RESET)

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        await spam_check(self.bot, message)


def setup(bot):
    bot.add_cog(antiSpam(bot))
