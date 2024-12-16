import nextcord
from nextcord.ext import commands
from transformers import BertTokenizer, BertForSequenceClassification, pipeline

# Tokenizerとモデルを初期化
model_name = "cl-tohoku/bert-base-japanese"
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name, num_labels=2)

# 感情分析パイプライン
classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

# 不適切な内容を判定する関数
def check_inappropriate_content(text):
    results = classifier(text)
    for result in results:
        if result['label'] == 'LABEL_1' and result['score'] > 0.8:  # スコアとラベルを調整
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
