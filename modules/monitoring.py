import nextcord
from nextcord.ext import commands
import requests
from datetime import timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Hugging Face APIキー
API_KEY = "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"

# Hugging Faceの感情分析用APIエンドポイント
API_URL = "https://api-inference.huggingface.co/models/unitary/toxic-bert"

# VADERのインスタンス作成
vader_analyzer = SentimentIntensityAnalyzer()

# Hugging Faceを使って暴言の検出
def detect_toxicity_huggingface(text):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {"inputs": text}

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()  # HTTPエラーがあれば例外をスロー

        result = response.json()
        if response.status_code == 200 and isinstance(result, list):
            for label_info in result[0]:
                label = label_info.get("label", "")
                score = label_info.get("score", 0)
                print(f"Label: {label}, Score: {score}")  # デバッグ用出力
                if label in ["toxic", "insult", "threat"] and score > 0.3:
                    return label, score
        else:
            print(f"Error: Unexpected status code {response.status_code}")

    except requests.exceptions.RequestException as e:  # HTTPリクエストエラーをキャッチ
        print(f"Error during API request: {e}")
    except Exception as e:  # その他の例外をキャッチ
        print(f"Unexpected error: {e}")
    return None, None

# VADERを使って感情分析を実施
def detect_sentiment_vader(text):
    sentiment = vader_analyzer.polarity_scores(text)
    # VADERのポジティブスコアが低く、ネガティブスコアが高い場合に危険と判断
    if sentiment['compound'] < -0.3:
        return "toxic", sentiment['compound']
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

        # まずVADERで感情分析を行い、暴言を検出
        label, score = detect_sentiment_vader(message.content)

        # VADERで暴言が検出された場合
        if label == "toxic" and score < -0.3:
            try:
                await message.delete()  # メッセージを削除
                await message.author.timeout(timedelta(minutes=30), reason="VADER検出: 暴言または脅迫が検出されました。")
                await message.channel.send(f"{message.author.mention} 暴言/脅迫が検出されたため、30分のタイムアウトを適用しました。")
                return  # VADERで検出された場合は処理を終了

        # もしVADERで検出されなかった場合、Hugging Faceで再度検出
        label, score = detect_toxicity_huggingface(message.content)

        # Hugging Faceで暴言が検出された場合
        if label == "toxic" and score > 0.3:
            try:
                await message.delete()  # メッセージを削除
                await message.author.timeout(timedelta(minutes=30), reason="Hugging Face検出: 暴言または脅迫が検出されました。")
                await message.channel.send(f"{message.author.mention} 暴言/脅迫が検出されたため、30分のタイムアウトを適用しました。")
            except Exception as e:
                print(f"タイムアウト適用エラー: {e}")

        # メッセージの処理を次のイベントに渡す
        await self.bot.process_commands(message)

def setup(bot):
    bot.add_cog(monitoring(bot))
