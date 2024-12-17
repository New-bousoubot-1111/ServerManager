import nextcord
import json
import requests
import datetime
from PIL import Image

with open('json/config.json','r') as f:
	config = json.load(f)

color = nextcord.Colour(int(config['color'],16))

#エラー展開
class open_error(nextcord.ui.View):
  def __init__(self,embed,embed2):
    super().__init__(timeout=None)
    self.value = None
    self.embed = embed
    self.embed2 = embed2

  @nextcord.ui.button(label="エラーを展開",style=nextcord.ButtonStyle.red)
  async def open_the_error(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
    await interaction.response.edit_message(embed=self.embed2,view=close_error(self.embed,self.embed2))

class close_error(nextcord.ui.View):
  def __init__(self,embed,embed2):
    super().__init__(timeout=None)
    self.value = None
    self.embed = embed
    self.embed2 = embed2

  @nextcord.ui.button(label="エラーを閉じる",style=nextcord.ButtonStyle.red)
  async def close_the_error(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
    await interaction.response.edit_message(embed=self.embed,view=open_error(self.embed,self.embed2))

#ページボタン
class help_page(nextcord.ui.View):
  def __init__(self,embed,embed2):
    super().__init__(timeout=None)
    self.value = None
    self.embed = embed
    self.embed2 = embed2

  @nextcord.ui.button(label="情報",style=nextcord.ButtonStyle.green)
  async def close_the_error(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
    await interaction.response.edit_message(embed=self.embed)

  @nextcord.ui.button(label="コマンド",style=nextcord.ButtonStyle.green)
  async def open_the_error(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
    await interaction.response.edit_message(embed=self.embed2)
    
#管理者専用
def creator_only():
  embed=nextcord.Embed(title="Error",description="このコマンドは管理者専用です",color=0xff0000)
  return embed

#起動時間
def sec_formatter(times):
  times = round(int(times))
  if times > 0:
    minutes, seconds = divmod(times, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

  times = []
  times.append(f"{days}日")
  times.append(f"{hours}時間")
  times.append(f"{minutes}分")
  times.append(f"{seconds}秒")
  times = ''.join(times)
  return times
