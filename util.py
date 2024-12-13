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

#地震ページ
class eew_page(nextcord.ui.View):
  def __init__(self,embed,embed2):
    super().__init__(timeout=None)
    self.value = None
    self.embed = embed
    self.embed2 = embed2
  @nextcord.ui.button(label="eew",style=nextcord.ButtonStyle.green)
  async def close_the_error(self,button:nextcord.ui.Button,interaction:nextcord.Interaction):
    await interaction.response.edit_message(embed=self.embed)
  @nextcord.ui.button(label="eew2",style=nextcord.ButtonStyle.green)
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
  
#地震
def eew_now():
  now = datetime.datetime.now() + datetime.timedelta(hours=8,minutes=59,seconds=59)
  format_time = now.strftime("%Y%m%d%H%M%S")
  return format_time

def eew_time():
  now = datetime.datetime.now() + datetime.timedelta(hours=8,minutes=59,seconds=59)
  format_time = now.strftime("%Y年%m月%d日 %H時")
  return format_time

def eew_origin_time(time):
  time = datetime.datetime.strptime(time,'%Y%m%d%H%M%S') - datetime.timedelta(hours=9)
  format_time = time.strftime("%M分")
  return format_time

def kyoshin_time():
  try:
    res = requests.get('http://www.kmoni.bosai.go.jp/webservice/server/pros/latest.json')
    if res.status_code == 200:
      try:
        data = res.json()
        time = data['latest_time'].replace("/","").replace(" ","").replace(":","")
      except:
        time = 0
      return time
  except:
    time = datetime.datetime.now()
    time = time + datetime.timedelta(hours=8,minutes=59,seconds=58)
    time = time.strftime("%Y%m%d%H%M%S")
    return time

#強震モニタ
async def eew_image(eew_channel):
  try:
    time = kyoshin_time()
  except:
    pass
    return
  rgal = requests.get(f'https://smi.lmoniexp.bosai.go.jp/data/map_img/RealTimeImg/acmap_s/{time[:-6]}/{time}.acmap_s.gif')
  with open('images/gal.gif','wb') as f:
    f.write(rgal.content)
  rpsw = requests.get(f'https://smi.lmoniexp.bosai.go.jp/data/map_img/PSWaveImg/eew/{time[:-6]}/{time}.eew.gif')
  with open('images/pseew.gif','wb') as f:
    f.write(rpsw.content)
  rewa = requests.get(f'https://smi.lmoniexp.bosai.go.jp/data/map_img/EstShindoImg/eew/{time[:-6]}/{time}.eew.gif')
  with open('images/eewarea.gif','wb') as f:
    f.write(rewa.content)
  base = Image.open('images/base.gif').convert('RGBA')
  gal = Image.open('images/gal.gif').convert('RGBA')
  psw = Image.open('images/pseew.gif').convert('RGBA')
  if rgal.status_code != 200:
    pass
    return
  try:
    img = Image.alpha_composite(base,gal)
  except:
    img = Image.alpha_composite(base,base)
  try:
    img = Image.alpha_composite(img,psw)
  except:
    pass
  img.save('images/kmoni.png')
  sent_message = await eew_channel.send(file=nextcord.File('images/kmoni.png'))
  return sent_message.attachments[0].url
