import nextcord
from nextcord.ext import commands
from colorama import Fore
import random

# 認証コードを保持する辞書
auth_codes = {}

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
            color=nextcord.Colour.blue()
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
            color=nextcord.Colour.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="コードを取得", style=nextcord.ButtonStyle.green)
    async def auth_code(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # 認証コードを生成して保持
        answer = random.randint(100000, 999999)
        auth_codes[interaction.user.id] = str(answer)

        embed = nextcord.Embed(
            title="認証コード",
            description="以下の認証コードを2分以内に認証してください。",
            color=nextcord.Colour.gold()
        )
        embed.add_field(name="認証コード", value=str(answer), inline=False)

        # 認証用のボタン付きビューを送信
        await interaction.response.send_message(embed=embed, view=AuthCodeView(interaction.user.id), ephemeral=True)


# 認証用のView（認証ボタン付き）
class AuthCodeView(nextcord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @nextcord.ui.button(label="認証", style=nextcord.ButtonStyle.green)
    async def auth_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # 認証用Modalを表示
        await interaction.response.send_modal(AuthCodeModal(self.user_id))


# 認証コード入力用のModal
class AuthCodeModal(nextcord.ui.Modal):
    def __init__(self, user_id):
        super().__init__(title="認証コード入力")
        self.user_id = user_id

        self.code_input = nextcord.ui.TextInput(
            label="認証コード",
            placeholder="6桁のコードを入力してください",
            style=nextcord.TextInputStyle.short,
            min_length=6,
            max_length=6
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: nextcord.Interaction):
        # デバッグメッセージを追加
        print(f"ユーザーID: {self.user_id}, 入力コード: {self.code_input.value}")

        # 保存された認証コードを取得
        saved_code = auth_codes.get(self.user_id)

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
                # 認証コードを削除
                auth_codes.pop(self.user_id, None)
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


def setup(bot):
    bot.add_cog(auth(bot))
