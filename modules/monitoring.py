import nextcord
from nextcord.ext import commands
import openai
import os

class monitoring(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # OpenAIのAPIキー
        openai.api_key = os.getenv("openai_key")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return  # Botのメッセージは無視

        # OpenAI APIでメッセージを解析 (新しいインターフェースを使用)
        try:
            response = openai.chat.Completion.create(
                model="gpt-3.5-turbo",  # 使用するモデルを指定
                messages=[
                    {"role": "system", "content": "あなたは親切なアシスタントです。"},
                    {"role": "user", "content": message.content}
                ]
            )

            result = response['choices'][0]['message']['content'].strip()
            if "不適切" in result:  # 「不適切」と判定された場合
                await message.delete()  # メッセージを削除
                await message.channel.send(f"{message.author.mention} 不適切な言葉が検出されました。")
                
                # 処罰例 (警告の送信)
                await message.author.send("不適切な発言が検出されましたのでご注意ください。")
                return

        except Exception as e:
            print(f"Error while processing message: {e}")

        await self.bot.process_commands(message)  # コマンド処理を続行

# Cogとして設定
def setup(bot):
    bot.add_cog(monitoring(bot))
