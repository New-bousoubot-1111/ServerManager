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

        # OpenAI APIでメッセージを解析
        response = openai.Completion.create(
            engine="text-davinci-003",  # モデルを指定
            prompt=f"以下のメッセージが不適切かどうか判定してください:\n\n{message.content}\n\n不適切ならば「はい」、適切ならば「いいえ」と答えてください。",
            max_tokens=10,
        )

        result = response.choices[0].text.strip()
        if result == "はい":
            await message.delete()  # 不適切なメッセージを削除
            await message.channel.send(f"{message.author.mention} 不適切な言葉が検出されました。")
            
            # 処罰例 (警告の送信)
            await message.author.send("不適切な発言が検出されましたのでご注意ください。")
            return

        await self.bot.process_commands(message)  # コマンド処理を続行

# Cogとして設定
def setup(bot):
    bot.add_cog(monitoring(bot))
