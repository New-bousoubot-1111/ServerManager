import nextcord
from nextcord.ext import commands
import json
from colorama import Fore
import random

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

# 認証コマンドを扱うCog
class auth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|auth          |" + Fore.RESET)
    
    # 認証コマンド
    @nextcord.slash_command(description="認証")
    async def auth(self, ctx):
        embed = nextcord.Embed(title="必ずルールを全て読んでから認証をして下さい", description="", color=color)
        await ctx.send(embed=embed, view=auth_rule(), ephemeral=True)

# ルール表示ボタンの処理
class auth_rule(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="ルールを表示", style=nextcord.ButtonStyle.green)
    async def rule_show(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(
            title="ルール",
            description="1.他者が嫌がるようなことはしないでください。\n2.荒らすような行為はしないでください。\n3.他鯖の招待リンクの添付は控えて下さい。\n4.この鯖でBOTを使用する場合はコマンドチャンネルでお願いします。\n以上のルールを守るようお願いします！",
            color=color
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="コードを取得", style=nextcord.ButtonStyle.green)
    async def auth_code(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # 認証コードをランダムに生成
        answer = random.randint(100000, 999999)
        embed = nextcord.Embed(
            title="認証コード",
            description="2分以内にコードを認証してください",
            color=nextcord.Color.gold()
        )
        embed.add_field(name="パスワード", value=str(answer))
        await interaction.response.send_message(embed=embed, view=auth_code_view(answer), ephemeral=True)

# 認証コードを入力するためのフォーム
class auth_code_modal(nextcord.ui.Modal):
    def __init__(self, user_id, generated_code):
        super().__init__(title="認証コード入力")
        self.user_id = user_id
        self.generated_code = generated_code
        self.code_input = nextcord.ui.TextInput(
            label="認証コード",
            placeholder="コードを入力してください (6桁)",
            style=nextcord.TextInputStyle.short,
            min_length=6,
            max_length=6
        )
        self.add_item(self.code_input)

    # フォーム送信時の処理
    async def on_submit(self, interaction: nextcord.Interaction):
        # 入力されたコードを取得
        input_code = self.code_input.value
        print(f"入力されたコード: {input_code}")  # デバッグログ

        # 認証コードが一致するかチェック
        if input_code == str(self.generated_code):
            role = nextcord.utils.get(interaction.guild.roles, name="user")
            if role:
                await interaction.user.add_roles(role)
                embed = nextcord.Embed(
                    title="認証成功",
                    description="userロールを付与しました。",
                    color=0x00ffee
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = nextcord.Embed(
                    title="エラー",
                    description="userロールが見つかりませんでした。",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = nextcord.Embed(
                title="認証失敗",
                description="認証コードが正しくありません。",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# 認証コード生成後に表示されるボタン
class auth_code_view(nextcord.ui.View):
    def __init__(self, generated_code):
        super().__init__(timeout=None)
        self.generated_code = generated_code

    @nextcord.ui.button(label="認証コードを入力", style=nextcord.ButtonStyle.green)
    async def auth_code_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # モーダルを表示するためにユーザーIDと生成されたコードを渡す
        await interaction.response.send_modal(auth_code_modal(interaction.user.id, self.generated_code))

def setup(bot):
    return bot.add_cog(auth(bot))
