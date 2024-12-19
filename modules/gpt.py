from nextcord.ext import commands
from transformers import pipeline

class gpt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # NLPモデルの準備（例: GPT-2）
        self.nlp = pipeline("text-generation", model="gpt2")

    @commands.Cog.listener()
    async def on_message(self, message):
        # ボット自身のメッセージには反応しない
        if message.author == self.bot.user:
            return
        
        # NLPモデルで応答を生成
        response = self.nlp(message.content, max_length=50, num_return_sequences=1)[0]['generated_text']
        
        # 応答を送信
        await message.channel.send(response)

# Cogをセットアップするための関数
def setup(bot):
    bot.add_cog(gpt(bot))
