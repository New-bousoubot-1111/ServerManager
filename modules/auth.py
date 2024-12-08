import nextcord
from nextcord.ext import commands
import json
import random

class auth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(description="認証")
    async def auth(self, ctx):
        embed = nextcord.Embed(
            title="必ずルールを全て読んでから認証をして下さい",
            color=nextcord.Colour.blue()
        )
        await ctx.send(embed=embed, view=AuthView(), ephemeral=True)


class AuthView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="ルールを表示",style=nextcord.ButtonStyle.green)
    async def rule_show(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
      embed=nextcord.Embed(title="ルール", description="1.他者が嫌がるようなことはしないでください。\n2.荒らすような行為はしないでください。\n3.他鯖の招待リンクの添付は控えて下さい。\n4.この鯖でBOTを使用する場合はコマンドチャンネルでお願いします。\n以上のルールを守るようお願いします！",color=color)
      await interaction.response.send_message(embed=embed,ephemeral=True)
	
    @nextcord.ui.button(label="認証コードを取得", style=nextcord.ButtonStyle.green)
    async def generate_code(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # ランダムな認証コード生成
        answer = random.randint(100000, 999999)
        with open('json/id.json', 'w') as f:
            json.dump({"auth": str(answer)}, f, indent=2)

        embed = nextcord.Embed(
            title="認証コード",
            description=f"2分以内に以下のコードを認証してください。\n`{answer}`",
            color=nextcord.Colour.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        # 認証ボタンを表示するViewを送信
        await interaction.followup.send("コードを入力してください。", view=AuthInputView(), ephemeral=True)


class AuthInputView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="認証", style=nextcord.ButtonStyle.green)
    async def auth_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Modalを表示
        await interaction.response.send_modal(AuthCodeModal())


class AuthCodeModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="認証コード入力")
        self.code_input = nextcord.ui.TextInput(
            label="認証コード",
            placeholder="6桁のコードを入力してください",
            min_length=6,
            max_length=6
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: nextcord.Interaction):
        # JSONファイルから認証コードを取得
        with open('json/id.json', 'r') as f:
            saved_code = json.load(f).get('auth')

        # 入力されたコードを取得
        input_code = self.code_input.value
        if input_code == saved_code:
            # 認証成功: ロールを付与
            role = nextcord.utils.get(interaction.guild.roles, name="user")
            if role:
                await interaction.user.add_roles(role)
                embed = nextcord.Embed(
                    title="認証成功",
                    description="userロールを付与しました。",
                    color=nextcord.Colour.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # ロールが見つからない
                embed = nextcord.Embed(
                    title="エラー",
                    description="付与するロールが見つかりません。",
                    color=nextcord.Colour.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # 認証失敗
            embed = nextcord.Embed(
                title="認証失敗",
                description="認証コードが正しくありません。",
                color=nextcord.Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(auth(bot))
