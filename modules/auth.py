import nextcord
from nextcord.ext import commands
import random
import string
import json
from colorama import Fore

with open('json/config.json','r') as f:
	config = json.load(f)

color = nextcord.Colour(int(config['color'],16))
# 認証コードを保存する辞書 (ユーザーIDをキー、認証コードを値にする)
auth_codes = {}

class auth(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
		
  @commands.Cog.listener()
  async def on_ready(self):
    print(Fore.BLUE + "|auth          |" + Fore.RESET)

# 認証コードを生成するコマンド
  @bot.slash_command(description="認証コードを生成します")
  async def auth(interaction: nextcord.Interaction):
      user = interaction.user
      code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
      auth_codes[user.id] = code
      await interaction.response.send_message(f"あなたの認証コードは: **{code}** です。このコードを次のフォームに入力してください。", ephemeral=True)

# 認証コード入力用のフォーム
class AuthModal(nextcord.ui.Modal):
    def __init__(self, role_id):
        super().__init__(
            title="認証コード入力",
        )
        self.code_input = nextcord.ui.TextInput(
            label="認証コード",
            placeholder="認証コードを入力してください。",
            required=True
        )
        self.add_item(self.code_input)
        self.role_id = role_id

    async def callback(self, interaction: nextcord.Interaction):
        user = interaction.user
        input_code = self.code_input.value
        # 入力されたコードをチェック
        if auth_codes.get(user.id) == input_code:
            # ユーザーにロールを付与
            guild = interaction.guild
            role = guild.get_role(self.role_id)
            member = guild.get_member(user.id)

            if role and member:
                await member.add_roles(role)
                await interaction.response.send_message("認証に成功しました！ロールを付与しました。", ephemeral=True)
                # 認証コードを削除
                del auth_codes[user.id]
            else:
                await interaction.response.send_message("ロールの付与に失敗しました。管理者にお問い合わせください。", ephemeral=True)
        else:
            await interaction.response.send_message("認証コードが一致しません。もう一度お試しください。", ephemeral=True)

# 認証フォームを開くコマンド
  @bot.slash_command(description="認証フォームを開きます")
  async def verify(interaction: nextcord.Interaction):
      await interaction.response.send_modal(AuthModal(role_id))

# 認証用のロールID
ROLE_ID = 1041002647827791932  # ロールIDを設定

def setup(bot):
  return bot.add_cog(auth(bot))
