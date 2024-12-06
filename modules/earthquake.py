import nextcord
from nextcord.ext import commands,tasks
import json
import requests
from colorama import Fore
from replit import db
import util

with open('json/config.json','r') as f:
	config = json.load(f)

color = nextcord.Colour(int(config['color'],16))

class earthquake(commands.Cog):
  def __init__(self, bot, db):
    self.bot = bot
    self.id = None
    self.db = db
		
  @commands.Cog.listener()
  async def on_ready(self):
    print(Fore.BLUE + "|earthquake    |" + Fore.RESET)
    self.eew_check.start()
    self.eew_info.start()
    
  #緊急地震速報
  @tasks.loop(seconds=2)
  async def eew_check(self):
    now = util.eew_now()
    if now == 0:
      return		
    res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/{now}.json")
    if res.status_code == 200:
      data = res.json()
      cache = json.loads(db['cache'])			
      if data['result']['message'] == "":
        if cache['report_time'] != data['report_time']:
          eew_channel = self.bot.get_channel(int(config['eew_channel']))
          image = False					
          if data['is_training'] == True:
            return
          if data['is_cancel'] == True:
            embed=nextcord.Embed(title="緊急地震速報がキャンセルされました",description="先ほどの緊急地震速報はキャンセルされました",color=color)
            await eew_channel.send(embed=embed)					
            return
          if data['alertflg'] == "予報":
            start_text = ""					
            if data['is_final'] == False:
              title = f"緊急地震速報 第{data['report_num']}報(予報)"
              color2 = 0x00ffee #ブルー
            else:
              title = f"緊急地震速報 最終報(予報)"
              color2 = 0x00ffee #ブルー
              image = True						
            if data['calcintensity'] in ["5強","6弱","6強","7"]:
              start_text = ""						
          if data['alertflg'] == "警報":
            start_text = "<@&1192026173924970518>\n**誤報を含む情報の可能性があります。\n今後の情報に注意してください**\n"	
            if data['is_final'] == False:					
              title = f"緊急地震速報 第{data['report_num']}報(警報)"
              color2 = 0xff0000 #レッド
            else:
              title = f"緊急地震速報 最終報(警報)"
              color2 = 0xff0000 #レッド
              image = True						

          time = util.eew_time()
          time2 = util.eew_origin_time(data['origin_time'])
          embed=nextcord.Embed(title=title,description=f"{start_text}{time}{time2}頃、**{data['region_name']}**で地震が発生しました。\n最大予想震度は**{data['calcintensity']}**、震源の深さは**{data['depth']}**、マグニチュードは**{data['magunitude']}**と推定されます。",color=color2)
          await eew_channel.send(embed=embed)
          if data['report_num'] == "1":
            image = True
          if image == True:					
            await util.eew_image(eew_channel)
        db['cache'] = str(data)
        db['cache'] = db['cache'].replace("True","true").replace("False","false").replace("'",'"')

  #地震情報
  @tasks.loop(seconds=2)
  async def eew_info(self):
    with open('json/id.json','r') as f:
      id = json.load(f)['eew_id']
      data = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1').json()[0]["points"]
      if data[0]["isArea"] is False:
        isArea = "この地震による津波の心配はありません" if not data[0]["isArea"] else "この地震で津波が発生する可能性があります"
    request = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1')
    response = request.json()[0]
    data = response['earthquake']
    hypocenter = data['hypocenter']
    if request.status_code == 200:
      if id != response['id']:
        embed=nextcord.Embed(title="地震情報",color=color)
        embed.add_field(name="発生時刻",value=data['time'],inline=False)
        embed.add_field(name="震源地",value=hypocenter['name'],inline=False)
        embed.add_field(name="最大震度",value=round(data['maxScale']/10),inline=False)
        embed.add_field(name="マグニチュード",value=hypocenter['magnitude'],inline=False)
        embed.add_field(name="震源の深さ",value=f"{hypocenter['depth']}Km",inline=False)
        embed.add_field(name="",value=isArea,inline=False)
        embed.set_footer(text=data['time'])
        eew_channel = self.bot.get_channel(int(config['eew_channel']))
        await eew_channel.send(embed=embed)
        with open('json/id.json','r') as f:
          id = json.load(f)
          id['eew_id'] = response['id']
        with open('json/id.json','w') as f:
          json.dump(id,f,indent=2)
      else:
        return

def setup(bot):
  return bot.add_cog(earthquake(bot))
