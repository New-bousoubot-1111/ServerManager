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
		
  @commands.Cog.listener()
  async def on_ready(self):
    print(Fore.BLUE + "|auth          |" + Fore.RESET)
    
  #認証コマンド
  @nextcord.slash_command(description="認証")
  async def auth(self,ctx):
    embed=nextcord.Embed(title="必ずルールを全て読んでから認証をして下さい", description="",color=color)
    await ctx.send(embed=embed,view=auth_rule(),ephemeral=True)

#ルール表示
class auth_rule(nextcord.ui.View):
  def __init__(self):
    super().__init__(timeout=None)

  @nextcord.ui.button(label="ルールを表示",style=nextcord.ButtonStyle.green)
  async def rule_show(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
    embed=nextcord.Embed(title="ルール", description="1.他者が嫌がるようなことはしないでください。\n2.荒らすような行為はしないでください。\n3.他鯖の招待リンクの添付は控えて下さい。\n4.この鯖でBOTを使用する場合はコマンドチャンネルでお願いします。\n以上のルールを守るようお願いします！",color=color)
    await interaction.response.send_message(embed=embed,ephemeral=True)

  @nextcord.ui.button(label="コードを取得",style=nextcord.ButtonStyle.green)
  async def auth_code(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
    answer = random.randint(100000, 999999)
    embed = nextcord.Embed(
    title="認証コード",
    description="2分以内にコードを認証してください",
    color=nextcord.Color.gold()
    )
    embed.add_field(name="パスワード", value=str(answer))
    await interaction.response.send_message(embed=embed,view=auth_code(),ephemeral=True)
    with open('json/id.json','r') as f:
      auth = json.load(f)
      auth['auth'] = f"{answer}"
      with open('json/id.json','w') as f:
        json.dump(auth,f,indent=2)

class auth_code2(nextcord.ui.Modal):
  def __init__(self):
    super().__init__("認証コード画面",timeout=None)
    self.add_item(nextcord.ui.TextInput(
			label="認証",
      placeholder="コードを入力して下さい(000000)",style=nextcord.TextInputStyle.paragraph,min_length=6,max_length=6))

  #callback
  async def on_submit(self,interaction:nextcord.Interaction):
    #global answer
    with open('json/id.json', 'r') as f:
      id = json.load(f)
      answer = "".join(f"{x}" for x in id['auth'])
      answer = "".join(answer)
      answer2 = self.auth_code2.value
      if answer2 == answer:
        role = nextcord.utils.get(interaction.guild.roles, name="user")
        await interaction.user.add_roles(role)
        embed=nextcord.Embed(title="userロールを付与しました",color=0x00ffee)
        await interaction.channel.send(embed=embed,ephemeral=True)
      else:
        embed=nextcord.Embed(title="userロールの付与に失敗しました",color=0xff0000,ephemeral=True)
        await interaction.channel.send(embed=embed)

class auth_code(nextcord.ui.View):
  def __init__(self):
    super().__init__(timeout=None)
    self.value = None

  @nextcord.ui.button(label="認証",style=nextcord.ButtonStyle.green)
  async def eval(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
      await interaction.response.send_modal(auth_code2())

def setup(bot):
  return bot.add_cog(auth(bot))