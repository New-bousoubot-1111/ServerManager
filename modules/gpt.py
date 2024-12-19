import os
import nextcord
from nextcord.ext import commands
import openai

# OpenAI APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

class api(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # Bot自身のメッセージは無視
        if message.author.bot:
            return

        # Botへのメンションに反応
        if self.bot.user in message.mentions:
            try:
                # ユーザーのメッセージをAPIに送信
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "あなたは親切で知識豊富なアシスタントです。"},
                        {"role": "user", "content": message.content}
                    ]
                )

                # 応答を取得して送信
                reply = response['choices'][0]['message']['content'].strip()
                await message.reply(reply)

            except Exception as e:
                # エラー処理
                print(f"Error: {e}")
                await message.reply("申し訳ありませんが、応答中にエラーが発生しました。")

# Cogの読み込み
@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")

bot.add_cog(MentionResponder(bot))
