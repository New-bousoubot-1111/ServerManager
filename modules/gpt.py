import os
import nextcord
from nextcord.ext import commands
import openai

# OpenAI APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

class gpt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # Bot自身のメッセージやDMは無視
        if message.author.bot or isinstance(message.channel, nextcord.DMChannel):
            return

        # Botへのメンションに反応
        if self.bot.user in message.mentions:
            try:
                # メンション部分を削除して純粋なメッセージを取得
                user_message = message.content.replace(f"<@{self.bot.user.id}>", "").strip()

                # OpenAI APIにリクエストを送信
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "あなたは親切で知識豊富なアシスタントです。"},
                        {"role": "user", "content": user_message}
                    ]
                )

                # OpenAIの応答を取得
                reply = response['choices'][0]['message']['content'].strip()

                # メッセージに返信
                await message.reply(reply)

            except Exception as e:
                # エラー時の処理
                print(f"Error: {e}")
                await message.reply("申し訳ありませんが、応答中にエラーが発生しました。")

# Cogのセットアップ
def setup(bot):
    bot.add_cog(gpt(bot))
