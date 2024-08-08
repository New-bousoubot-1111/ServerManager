import nextcord
import json
import os
import sys
import traceback
import ast
from replit import db
import util

with open('json/config.json','r') as f:
	config = json.load(f)

color = nextcord.Colour(int(config['color'],16))

def insert_returns(body):

  if isinstance(body[-1], ast.Expr):
    body[-1] = ast.Return(body[-1].value)
    ast.fix_missing_locations(body[-1])

  if isinstance(body[-1], ast.If):
    insert_returns(body[-1].body)
    insert_returns(body[-1].orelse)

  if isinstance(body[-1], ast.With):
    insert_returns(body[-1].body)

class eval_modal(nextcord.ui.Modal):
  def __init__(self):
    super().__init__("Eval")
    self.add_item(nextcord.ui.TextInput(
			label="Evalを実行したいコード",
      placeholder="print('HelloWorld')",
      style=nextcord.TextInputStyle.paragraph,
      min_length=1
		  ),
	  )

  async def callback(self,interaction:nextcord.Interaction):
    try:
      cmd = self.children[0].value
      name = "_eval_expr"
      cmds = "\n".join(f"  {i}" for i in cmd.splitlines())
      body = f"async def {name}():\n{cmds}"
      parsed = ast.parse(body)
      body = parsed.body[0].body
      insert_returns(body)
      env = {
				"self":self,
        "nextcord":nextcord,
				"bot":interaction.client,
        "interaction":interaction,
				"ctx":interaction,
				"os":os,
        "db":db,
        "__import__":__import__
      }
      exec(compile(parsed, filename="<ast>", mode="exec"), env)
      result = (await eval(f"{name}()", env))
      if result == None:
        result = "None"
      embed=nextcord.Embed(title="実行コード",description=f"```py\n{cmd}\n```",color=color)
      code = await interaction.channel.send(embed=embed)
      embed=nextcord.Embed(title="実行結果",description=f"```py\n{result}```",color=color)
      await code.reply(embed=embed)		
    except:
      embed=nextcord.Embed(title="実行コード",description=f"```py\n{cmd}\n```",color=color)
      code = await interaction.channel.send(embed=embed)
      embed=nextcord.Embed(title="エラー",description=f"```py\n{traceback.format_exc()}```",color=color)				
      await code.reply(embed=embed)

class devmenu_view(nextcord.ui.View):
  def __init__(self):
    super().__init__(timeout=None)
    self.value = None

  @nextcord.ui.button(label="Botを再起動",style=nextcord.ButtonStyle.green)
  async def restart(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
    if interaction.user.id in config['owners']:
      embed=nextcord.Embed(title="再起動",description="Botを再起動します\n再起動終了まで時間がかかる場合があります",color=color)
      await interaction.response.send_message(embed=embed)
      self.stop()
      res = sys.executable
      os.execl(res,res,*sys.argv)
    else:
      embed=util.creator_only()
      await interaction.response.send_message(embed=embed,ephemeral=True)

  @nextcord.ui.button(label="Evalを実行",style=nextcord.ButtonStyle.green)
  async def eval(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
    if interaction.user.id in config['owners']:
      await interaction.response.send_modal(eval_modal())
    else:
      embed=util.creator_only()
      await interaction.response.send_message(embed=embed,ephemeral=True)