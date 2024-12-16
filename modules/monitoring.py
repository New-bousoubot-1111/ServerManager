from transformers import pipeline
import nextcord
from nextcord.ext import commands
from datetime import timedelta

# 毒性検出モデルをロード
toxicity_classifier = pipeline("text-classification", model="unitary/toxic-bert")

class transformers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("| AI Profanity Filter Loaded |")

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        # ボットや管理者のメッセージを無視
        if message.author.bot or message.author.guild_permissions.administrator:
            return

        try:
            # メッセージを分析
            result = toxicity_classifier(message.content)
            toxicity_score = result[0]["score"]
            label = result[0]["label"]

            # 毒性スコアが高い場合にタイムアウト
            if label == "TOXIC" and toxicity_score > 0.8:  # スコアは0.0〜1.0
                await message.author.timeout(timedelta(hours=1), reason="暴言または脅迫が検出されました。")
                embed = nextcord.Embed(
                    description=f"{message.author.mention} 暴言/脅迫が検出されたため、1時間のタイムアウトを適用しました。",
                    color=0xFF0000,
                )
                await message.channel.send(embed=embed)
                await message.delete()

        except Exception as e:
            print(f"AIエラー: {e}")

def setup(bot):
    bot.add_cog(transformers(bot))
