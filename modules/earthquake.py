import nextcord
from nextcord.ext import commands,tasks
import json
import requests
from colorama import Fore
import util
import os

# 環境変数からキャッシュを取得
cache = json.loads(os.getenv("CACHE", '{"sent_reports": []}'))
# 変更後にキャッシュを更新
cache["sent_reports"].append("new_report_time")
os.environ["CACHE"] = json.dumps(cache)

# 初期化するキャッシュデータ
initial_cache = {"sent_reports": []}
# cache.json ファイルに書き込む
with open("json/cache.json", "w") as f:
    json.dump(initial_cache, f, indent=4)
print("キャッシュが初期化されました: cache.json に保存されました。")

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
    
  #緊急地震速報
  @tasks.loop(seconds=2)
  async def eew_check(self):
    now = util.eew_now()
    if now == 0:
        return
    res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/{now}.json")
    if res.status_code == 200:
        data = res.json()
        
        # キャッシュされた報告を確認
        sent_reports = self.cache.get("sent_reports", [])
        if data['report_time'] not in sent_reports:
            eew_channel = self.bot.get_channel(int(config['eew_channel']))
            image = False

            if data['is_training']:
                return

            if data['is_cancel']:
                embed = nextcord.Embed(
                    title="緊急地震速報がキャンセルされました",
                    description="先ほどの緊急地震速報はキャンセルされました",
                    color=0x00ffee
                )
                await eew_channel.send(embed=embed)
                return

            # 警報と予報の処理
            if data['alertflg'] == "予報":
                title = f"緊急地震速報 第{data['report_num']}報(予報)"
                color2 = 0x00ffee
            elif data['alertflg'] == "警報":
                title = f"緊急地震速報 第{data['report_num']}報(警報)"
                color2 = 0xff0000

            time = util.eew_time()
            embed = nextcord.Embed(
                title=title,
                description=f"{time}頃、**{data['region_name']}**で地震が発生しました。\n"
                            f"最大予想震度: **{data['calcintensity']}**\n"
                            f"深さ: **{data['depth']}**\n"
                            f"マグニチュード: **{data['magunitude']}**",
                color=color2
            )
            await eew_channel.send(embed=embed)

            # 送信済みリストに追加
            sent_reports.append(data['report_time'])
            self.cache['sent_reports'] = sent_reports


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
