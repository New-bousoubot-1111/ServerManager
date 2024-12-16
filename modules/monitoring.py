import nextcord
from nextcord.ext import commands
import requests
from datetime import timedelta

# Hugging Face APIキー
API_KEY = "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"

# Hugging Faceの感情分析用APIエンドポイント
API_URL = "https://api-inference.huggingface.co/models/unitary/toxic-bert"

# ユーザーが送信したメッセージの暴言を検出する関数
def detect_toxicity(text):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {"inputs": text}

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        label = result[0]["label"]
        score = result[0]["score"]
        return label, score
    else:
        print(f"Error: {response.status_code}")
        return None, None

class monitoring(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("| Profanity Filter Loaded |")

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        # ボットのメッセージや管理者のメッセージは無視
        if message.author.bot or message.author.guild_permissions.administrator:
            return

        # メッセージの内容をHugging Face APIで分析
        label, score = detect_toxicity(message.content)

        # 結果に基づいてタイムアウトや警告を行う
        if label == "TOXIC" and score > 0.8:  # スコアが0.8以上で暴言と見なす
            try:
                await message.author.timeout(timedelta(minutes=30), reason="暴言または脅迫が検出されました。")
                await message.channel.send(f"{message.author.mention} 暴言/脅迫が検出されたため、30分のタイムアウトを適用しました。")
                await message.delete()
            except Exception as e:
                print(f"タイムアウト適用エラー: {e}")

        # メッセージの処理を次のイベントに渡す
        await self.bot.process_commands(message)

def setup(bot):
    bot.add_cog(monitoring(bot))
