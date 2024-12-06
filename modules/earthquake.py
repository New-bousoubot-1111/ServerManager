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
  def __init__(self, bot):
    self.bot = bot
    self.id = None
		
  @commands.Cog.listener()
  async def on_ready(self):
    print(Fore.BLUE + "|earthquake    |" + Fore.RESET)
    self.eew_check.start()
    self.eew_info.start()
    
    
  if 'reported_nums' not in db:
    db['reported_nums'] = json.dumps([])
    
  #緊急地震速報
@tasks.loop(seconds=2)
async def eew_check(self):
    # 初期化処理
    if 'reported_nums' not in db:
        db['reported_nums'] = json.dumps([])  # 空リストで初期化
    if 'cache' not in db:
        db['cache'] = json.dumps({"report_time": ""})  # キャッシュを初期化

    now = util.eew_now()
    if now == 0:
        return

    res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/{now}.json")
    if res.status_code == 200:
        data = res.json()

        reported_nums = json.loads(db['reported_nums'])
        report_num = data['report_num']

        if report_num not in reported_nums:
            if len(reported_nums) >= 100:
                # リストが最大長に達したら、一番古いエントリを削除
                reported_nums.pop(0)

            reported_nums.append(report_num)
            db['reported_nums'] = json.dumps(reported_nums)

            cache = json.loads(db['cache'])
            if data['result']['message'] == "" and cache['report_time'] != data['report_time']:
                eew_channel = self.bot.get_channel(int(config['eew_channel']))
                image = False
                if data['is_training']:
                    return

                if data['is_cancel']:
                    embed = nextcord.Embed(
                        title="緊急地震速報がキャンセルされました",
                        description="先ほどの緊急地震速報はキャンセルされました",
                        color=0x00ffee,
                    )
                    await eew_channel.send(embed=embed)
                    return

                # 通知のためのコード
                alertdict = {
                    "予報": {"color": 0x00ffee, "prefix": ""},
                    "警報": {
                        "color": 0xff0000,
                        "prefix": "<@&1192026173924970518>\n**誤報を含む情報の可能性があります。\n今後の情報に注意してください**\n",
                    },
                }
                alertprop = alertdict[data['alertflg']]
                title = (
                    f"緊急地震速報 第{data['report_num']}報({data['alertflg']})"
                    if not data['is_final']
                    else f"緊急地震速報 最終報({data['alertflg']})"
                )
                if data['is_final']:
                    image = True

                time = util.eew_time()
                time2 = util.eew_origin_time(data['origin_time'])
                description = (
                    f"{alertprop['prefix']}{time}{time2}頃、**{data['region_name']}**で地震が発生しました。"
                    f"最大予想震度は**{data['calcintensity']}**、震源の深さは**{data['depth']}**、"
                    f"マグニチュードは**{data['magunitude']}**と推定されます。"
                )
                embed = nextcord.Embed(title=title, description=description, color=alertprop['color'])
                await eew_channel.send(embed=embed)
                if data['report_num'] == "1" or image:
                    await util.eew_image(eew_channel)

  


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
