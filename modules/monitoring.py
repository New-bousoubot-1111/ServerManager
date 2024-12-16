import nextcord
from nextcord.ext import commands
import requests
import json

API_KEY = "YOUR_PERSPECTIVE_API_KEY"  # ここにAPIキーを入れてください

def check_toxicity(text):
    url = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
    headers = {"Content-Type": "application/json"}
    data = {
        "comment": {"text": text},
        "languages": ["ja"],
        "requestedAttributes": {"TOXICITY": {}},
    }
    params = {"key": API_KEY}

    response = requests.post(url, headers=headers, params=params, json=data)
    response_json = response.json()

    toxicity_score = response_json["attributeScores"]["TOXICITY"]["summaryScore"]["value"]
    return toxicity_score

class monitoring(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("| Profanity Filter Loaded |")

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        # ボットや管理者のメッセージを無視
        if message.author.bot or message.author.guild_permissions.administrator:
            return

        # Perspective APIでメッセージをチェック
        toxicity_score = check_toxicity(message.content)

        if toxicity_score > 0.8:  # スコアが0.8を超えるとタイムアウト
            await message.author.timeout(timedelta(hours=1), reason="暴言または脅迫が検出されました。")
            embed = nextcord.Embed(
                description=f"{message.author.mention} 暴言/脅迫が検出されたため、1時間のタイムアウトを適用しました。",
                color=0xFF0000,
            )
            await message.channel.send(embed=embed)
            await message.delete()

def setup(bot):
    bot.add_cog(monitoring(bot))
