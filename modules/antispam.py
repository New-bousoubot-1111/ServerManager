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
target_channel = "1192117995561033768"

messages: Dict[int, List[nextcord.Message]] = {}  # ユーザーごとのメッセージ追跡
violations: Dict[int, int] = {}  # ユーザーごとのスパム違反回数


def format_exception(exc: Exception) -> str:
    """エラー内容をフォーマット"""
    return ''.join(traceback.TracebackException.from_exception(exc).format())


async def delete_messages(channel: nextcord.TextChannel, msgs: List[nextcord.Message]) -> None:
    """指定されたメッセージを削除"""
    for chunk in [msgs[i:i + 100] for i in range(0, len(msgs), 100)]:
        await channel.delete_messages(chunk)


class BanAppealModal(nextcord.ui.Modal):
    """バンされたユーザーが内容を送信するモーダル"""
    def __init__(self, bot: commands.Bot, target_channel_id: int, user: nextcord.User):
        self.bot = bot
        self.target_channel_id = target_channel_id
        self.user = user
        super().__init__(
            title="バン解除リクエスト",
            timeout=300,  # 5分
        )

        self.add_item(
            nextcord.ui.TextInput(
                label="リクエスト内容",
                placeholder="バンの理由や解除理由を入力してください",
                style=nextcord.TextInputStyle.paragraph,
                max_length=1000,
            )
        )

    async def callback(self, interaction: nextcord.Interaction):
        content = self.children[0].value  # ユーザーが入力した内容
        if target_channel is None:
            await interaction.response.send_message("送信先のチャンネルが見つかりませんでした。", ephemeral=True)
            return

        embed = nextcord.Embed(
            title="バン解除リクエスト",
            description=f"ユーザー: {self.user.mention} ({self.user.id})\n\n**内容:**\n{content}",
            color=0x00FF00,
        )
        await target_channel.send(embed=embed)
        await interaction.response.send_message("リクエストを送信しました。", ephemeral=True)


class BanAppealView(nextcord.ui.View):
    """モーダルを表示するためのボタン"""
    def __init__(self, bot: commands.Bot, target_channel_id: int, user: nextcord.User):
        super().__init__(timeout=None)
        self.bot = bot
        self.target_channel_id = target_channel_id
        self.user = user

    @nextcord.ui.button(label="リクエストを送信", style=nextcord.ButtonStyle.green)
    async def send_request(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = BanAppealModal(self.bot, self.target_channel_id, self.user)
        await interaction.response.send_modal(modal)


async def handle_violation(bot: commands.Bot, message: nextcord.Message):
    """スパム検出時の処理"""
    user_id = message.author.id
    member = message.author
    channel = message.channel
    appeal_channel_id = 123456789012345678  # バン解除リクエストを送信するチャンネルのIDを指定

    # ユーザーの違反回数を記録
    if user_id not in violations:
        violations[user_id] = 0
    violations[user_id] += 1
    level = violations[user_id]

    try:
        if level == 1:
            await member.timeout(timedelta(hours=1), reason="スパム行為 - 1回目")
            await channel.send(f"{member.mention}がスパム行為のため、1時間タイムアウトされました。")

        elif level == 2:
            await member.timeout(timedelta(days=1), reason="スパム行為 - 2回目")
            await channel.send(f"{member.mention}がスパム行為のため、1日タイムアウトされました。")

        elif level == 3:
            await member.kick(reason="スパム行為 - 3回目")
            await channel.send(f"{member.mention}がスパム行為のため、サーバーからキックされました。")

        elif level >= 4:
            await member.ban(reason="スパム行為 - 4回目以上")
            await channel.send(f"{member.mention}がスパム行為のため、サーバーからバンされました。")

            # バンされたユーザーにDMを送信
            try:
                appeal_view = BanAppealView(bot, appeal_channel_id, member)
                dm_channel = await member.create_dm()
                embed = nextcord.Embed(
                    title="バン解除リクエスト",
                    description="スパム行為によりバンされました。\n\n以下のボタンをクリックして、解除リクエストを送信してください。",
                    color=0xFF0000,
                )
                await dm_channel.send(embed=embed, view=appeal_view)
            except Exception as e:
                print(f"DM送信エラー: {format_exception(e)}", file=sys.stderr)

    except Exception as e:
        print(format_exception(e), file=sys.stderr)


async def spam_check(bot: commands.Bot, message: nextcord.Message) -> None:
    """スパム行為を検出"""
    if message.author.bot or message.author.id in EXCLUDED_USERS:
        return

    user_id = message.author.id
    if user_id not in messages:
        messages[user_id] = []

    messages[user_id].append(message)

    async def remove_message():
        if user_id in messages:
            messages[user_id] = [msg for msg in messages[user_id] if msg.id != message.id]

    bot.loop.call_later(SPAM_TIMEOUT, asyncio.create_task, remove_message())

    if len(messages[user_id]) > 10:
        await handle_violation(bot, message)
        await delete_messages(message.channel, messages[user_id])
        messages[user_id].clear()


class antispam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|antispam      |" + Fore.RESET)

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        await spam_check(self.bot, message)


def setup(bot):
    bot.add_cog(antispam(bot))
