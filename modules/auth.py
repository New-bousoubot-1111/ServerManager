import nextcord
from nextcord.ext import commands
import random
import string
import json
from colorama import Fore

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

# 認証コードを保存する辞書 (ユーザーIDをキー、認証コードを値にする)
auth_codes = {}
# 認証用のロールID
role_id = 1041002647827791932

class auth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|auth          |" + Fore.RESET)

    # 認証コードを生成するコマンド
    @nextcord.slash_command(description="認証コードを生成します")
    async def auth(self, interaction: nextcord.Interaction):
        user = interaction.user
        code = ''.join(random.choices(string.digits, k=6))
        auth_codes[user.id] = code
        embed = nextcord.Embed(title="必ずルールを全て読んでから認証をして下さい", description="", color=color)
        await interaction.response.send_message(embed=embed, view=auth_rule(), ephemeral=True)

    # 認証用のルールとコード取得ボタンのビュー
class auth_rule(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="ルールを表示", style=nextcord.ButtonStyle.green)
    async def rule_show(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(
            title="ルール",
            description="1. 他者が嫌がるようなことはしないでください。\n"
                        "2. 荒らすような行為はしないでください。\n"
                        "3. 他鯖の招待リンクの添付は控えて下さい。\n"
                        "4. この鯖でBOTを使用する場合はコマンドチャンネルでお願いします。\n"
                        "以上のルールを守るようお願いします！",
            color=color
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="コードを取得", style=nextcord.ButtonStyle.green)
    async def code_show(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        user = interaction.user
        code = ''.join(random.choices(string.digits, k=6))
        auth_codes[user.id] = code
        embed = nextcord.Embed(
            title="認証コード",
            description="2分以内にコードを認証してください",
            color=color
        )
        embed.add_field(name="パスワード", value=code)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# 認証コード入力用のフォーム
class AuthModal(nextcord.ui.Modal):
    def __init__(self, role_id):
        super().__init__(title="認証コード入力")
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
@nextcord.slash_command(description="認証フォームを開きます")
async def verify(self, interaction: nextcord.Interaction):
    await interaction.response.send_modal(self.AuthModal(role_id))

def setup(bot):
    bot.add_cog(auth(bot))
