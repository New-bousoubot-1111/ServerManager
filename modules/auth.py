import nextcord
from nextcord.ext import commands
import json
from colorama import Fore
import random

# 設定ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))


class auth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|auth          |" + Fore.RESET)

    # 認証コマンド
    @nextcord.slash_command(description="認証")
    async def auth(self, ctx):
        embed = nextcord.Embed(
            title="必ずルールを全て読んでから認証をして下さい",
            description="",
            color=color
        )
        await ctx.send(embed=embed, view=AuthRuleView(), ephemeral=True)


# ルール表示用のView
class AuthRuleView(nextcord.ui.View):
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
    async def auth_code(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # 認証コードを生成
        answer = random.randint(100000, 999999)
        with open('json/id.json', 'w') as f:
            json.dump({"auth": str(answer)}, f, indent=2)

        embed = nextcord.Embed(
            title="認証コード",
            description="2分以内に以下のコードを認証してください。",
            color=nextcord.Colour.gold()
        )
        embed.add_field(name="認証コード", value=str(answer), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        # 認証用ボタンを送信
        await interaction.followup.send("コードを入力してください。", view=AuthCodeView(), ephemeral=True)


# 認証コード入力用のModal
class AuthCodeModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="認証コード入力")

        self.code_input = nextcord.ui.TextInput(
            label="認証コード",
            placeholder="6桁のコードを入力してください",
            style=nextcord.TextInputStyle.short,
            min_length=6,
            max_length=6
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: nextcord.Interaction):
        # JSONファイルから認証コードを取得
        with open('json/id.json', 'r') as f:
            saved_code = json.load(f).get('auth')

        # 入力されたコードを比較
        input_code = self.code_input.value
        if input_code == saved_code:
            # 認証成功時
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
            # 認証失敗時
            embed = nextcord.Embed(
                title="認証失敗",
                description="認証コードが正しくありません。",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


# 認証用のView
class AuthCodeView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="認証", style=nextcord.ButtonStyle.green)
    async def auth_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # 認証用Modalを表示
        await interaction.response.send_modal(AuthCodeModal())


def setup(bot):
    bot.add_cog(auth(bot))
