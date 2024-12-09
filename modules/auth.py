import nextcord
from nextcord.ext import commands
import random
import string
import json
from colorama import Fore

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

auth_codes = {}
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
        self.code_show.disabled = True

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
        self.code_show.disabled = False
        await interaction.message.edit(view=self)

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
        embed.add_field(name="コード", value=code)
        await interaction.response.send_message(embed=embed, view=auth_form(), ephemeral=True)

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
        if auth_codes.get(user.id) == input_code:
            guild = interaction.guild
            role = guild.get_role(self.role_id)
            member = guild.get_member(user.id)

            if role and member:
                embed = nextcord.Embed(title="成功", description="認証に成功しました", color=color)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                del auth_codes[user.id]
            else:
                embed = nextcord.Embed(title="失敗", description="管理者にお問い合わせください", color=color)
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = nextcord.Embed(title="失敗", description="認証コードが一致しません", color=color)
            await interaction.response.send_message(embed=embed, ephemeral=True)

class auth_form(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    @nextcord.ui.button(label="認証", style=nextcord.ButtonStyle.green)
    async def eval(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(AuthModal(role_id))

def setup(bot):
    bot.add_cog(auth(bot))
