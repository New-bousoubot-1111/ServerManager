import asyncio
import sys
import traceback
from datetime import timedelta
from typing import Dict, List, Optional
import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Button
from colorama import Fore

SPAM_TIMEOUT = 15  # スパムメッセージの有効時間（秒）
BAN_APPEAL_CHANNEL_ID = None  # バン解除リクエストを送信するチャンネルID
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


class BanAppealView(View):
    """バン解除リクエスト用のビュー"""
    def __init__(self, bot, ban_appeal_channel, member):
        super().__init__(timeout=None)
        self.bot = bot
        self.ban_appeal_channel = ban_appeal_channel
        self.member = member

    @nextcord.ui.button(label="バン解除をリクエスト", style=nextcord.ButtonStyle.red)
    async def request_unban(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("リクエストを送信しました。処理をお待ちください。", ephemeral=True)
        embed = nextcord.Embed(
            title="バン解除リクエスト",
            description=(
                f"ユーザー {self.member.mention} がバン解除をリクエストしました。\n"
                f"ユーザーID: {self.member.id}"
            ),
            color=0x00FF00,
        )
        await self.ban_appeal_channel.send(embed=embed)


async def handle_violation(bot: commands.Bot, message: nextcord.Message):
    """スパム検出時の処理"""
    user_id = message.author.id
    member = message.author
    channel = message.channel
    ban_appeal_channel = bot.get_channel(BAN_APPEAL_CHANNEL_ID) if BAN_APPEAL_CHANNEL_ID else None

    # ユーザーの違反回数を記録
    if user_id not in violations:
        violations[user_id] = 0
    violations[user_id] += 4
    level = violations[user_id]

    try:
        if level == 1:
            # 1回目の処罰：1時間のタイムアウト
            await member.timeout(timedelta(hours=1), reason="スパム行為 - 1回目")
            embed = nextcord.Embed(
                description=f"{member.mention}はスパム行為のため、1時間タイムアウトされました。",
                color=0xFFFF00,
            )
            await channel.send(embed=embed)

        elif level == 2:
            # 2回目の処罰：1日のタイムアウト
            await member.timeout(timedelta(days=1), reason="スパム行為 - 2回目")
            embed = nextcord.Embed(
                description=f"{member.mention}はスパム行為のため、1日タイムアウトされました。",
                color=0xFFA500,
            )
            await channel.send(embed=embed)

        elif level == 3:
            # 3回目の処罰：サーバーからのキック
            await member.kick(reason="スパム行為 - 3回目")
            embed = nextcord.Embed(
                description=f"{member.mention}はスパム行為のため、サーバーからキックされました。",
                color=0xFF4500,
            )
            await channel.send(embed=embed)

        elif level >= 4:
            # 4回目以降の処罰：サーバーからのバン
            await member.ban(reason="スパム行為 - 4回目以上")
            embed = nextcord.Embed(
                description=f"{member.mention}はスパム行為のため、サーバーからバンされました。",
                color=0xFF0000,
            )
            await channel.send(embed=embed)

            # バンされたユーザーにDMを送信
            if ban_appeal_channel:
                try:
                    appeal_view = BanAppealView(bot, ban_appeal_channel, member)
                    dm_channel = await member.create_dm()

                    # DM送信を試みる
                    embed = nextcord.Embed(
                        title="バン解除リクエスト",
                        description="スパム行為によりバンされました。\n\n以下のボタンをクリックして、解除リクエストを送信してください。",
                        color=0xFF0000,
                    )
                    await dm_channel.send(embed=embed, view=appeal_view)

                except nextcord.Forbidden:
                    # DM送信が拒否された場合、管理者向けに通知
                    await ban_appeal_channel.send(
                        f"⚠️ {member.mention} にDMを送信できませんでした。"
                        f"DM送信を許可しているか確認してください。"
                    )

                except Exception as e:
                    # その他のエラーをログに記録
                    print(f"DM送信エラー: {format_exception(e)}", file=sys.stderr)
            else:
                print("バン解除リクエストチャンネルが設定されていません。")

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
    if len(messages[user_id]) > 10:  # 例: 10メッセージ以上送信するとスパム
        await handle_violation(bot, message)
        await delete_messages(message.channel, messages[user_id])
        messages[user_id].clear()  # スパム検出後、メッセージリストをクリア


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
