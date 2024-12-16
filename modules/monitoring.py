import nextcord
from nextcord.ext import commands
from transformers import pipeline

# 感情分析パイプラインの初期化
# ここでは `cl-tohoku/bert-base-japanese` モデルを使用
classifier = pipeline("text-classification", model="Mizuiro-sakura/luke-japanese-large-sentiment-analysis-wrime")

# 不適切な内容を判定する関数
def check_inappropriate_content(text):
    # メッセージの感情を分析
    results = classifier(text)
    for result in results:
        # スコアが高く、否定的 (negative) な感情と判断された場合
        if result['label'] == 'negative' and result['score'] > 0.8:
            return True
    return False

# Discord Bot の定義
class monitoring(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("| Profanity Filter Loaded |")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Bot自身のメッセージは無視
        if message.author.bot:
            return

        # メッセージの不適切な内容をチェック
        if check_inappropriate_content(message.content):
            # メッセージを削除
            await message.delete()
            # 警告メッセージを送信
            await message.channel.send(f"{message.author.mention} 不適切な発言が検出されました。メッセージは削除されました。")

            # 必要であればキックやバンを追加可能
            # await message.author.kick(reason="不適切な発言の使用")

def setup(bot):
    bot.add_cog(monitoring(bot))
