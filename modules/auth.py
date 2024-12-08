import nextcord
from nextcord.ext import commands
import json
from colorama import Fore
import random

with open('json/config.json','r') as f:
	config = json.load(f)

color = nextcord.Colour(int(config['color'],16))

class auth(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

	  
    @nextcord.slash_command(description="認証コマンド")
    async def auth(self, ctx):
        # ランダムな認証コードを生成
        auth_code = random.randint(100000, 999999)

        # 認証コードをJSONファイルに保存
        with open('auth_code.json', 'w') as f:
            json.dump({"auth_code": str(auth_code)}, f)

        # 認証コードを含むメッセージをユーザーに送信
        embed = nextcord.Embed(
            title="認証コードを取得しました。",
            description=f"認証コード: {auth_code}\n2分以内にコードを認証してください。",
            color=nextcord.Color.green()
        )
        await ctx.send(embed=embed, ephemeral=True)

        # 認証フォームの送信
        await ctx.send(
            "認証コードを入力してください。",
            view=AuthCodeView()
        )


class AuthCodeView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)  # タイムアウトを2分に設定

    @nextcord.ui.button(label="認証コードを入力", style=nextcord.ButtonStyle.green)
    async def auth_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # 認証コードを入力するためのモーダルを表示
        await interaction.response.send_modal(AuthCodeModal())


class AuthCodeModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="認証コードの入力")
        self.add_item(nextcord.ui.TextInput(
            label="認証コードを入力",
            placeholder="6桁の認証コードを入力してください",
            style=nextcord.TextInputStyle.short,
            min_length=6,
            max_length=6
        ))

    async def on_submit(self, interaction: nextcord.Interaction):
        # 入力されたコードを取得
        input_code = self.children[0].value

        # 保存された認証コードを読み込む
        with open('auth_code.json', 'r') as f:
            data = json.load(f)
            saved_code = data.get("auth_code")

        # 認証コードの一致を確認
        if input_code == saved_code:
            role = nextcord.utils.get(interaction.guild.roles, name="user")
            if role:
                await interaction.user.add_roles(role)
                embed = nextcord.Embed(
                    title="認証成功",
                    description="認証コードが一致しました。'user'ロールが付与されました。",
                    color=nextcord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = nextcord.Embed(
                    title="エラー",
                    description="userロールが見つかりませんでした。",
                    color=nextcord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = nextcord.Embed(
                title="認証失敗",
                description="入力した認証コードが正しくありません。",
                color=nextcord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

def setup(bot):
  return bot.add_cog(auth(bot))
