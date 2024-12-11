import nextcord
import json
import requests
import datetime
from PIL import Image
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from fuzzywuzzy import process
from nextcord import File, Embed
from datetime import datetime

ALERT_COLORS = {"Advisory": "purple", "Warning": "red", "Watch": "yellow"}
GEOJSON_PATH = "./images/japan.geojson"
GEOJSON_REGION_FIELD = 'nam'

# GeoJSONデータを読み込む
gdf = gpd.read_file(GEOJSON_PATH)

REGION_MAPPING = {
    "京都府": "Kyoto Fu",
    "佐賀県": "Saga Ken",
    "熊本県": "Kumamoto Ken",
    "香川県": "Kagawa Ken",
    "愛知県": "Aichi Ken",
    "栃木県": "Tochigi Ken",
    "山梨県": "Yamanashi Ken",
    "滋賀県": "Shiga Ken",
    "群馬県": "Gunma Ken",
    "宮城県": "Miyagi Ken",
    "静岡県": "Shizuoka Ken",
    "茨城県": "Ibaraki Ken",
    "沖縄県": "Okinawa Ken",
    "山形県": "Yamagata Ken",
    "和歌山県": "Wakayama Ken",
    "長崎県": "Nagasaki Ken",
    "秋田県": "Akita Ken",
    "岡山県": "Okayama Ken",
    "福岡県": "Fukuoka Ken",
    "岐阜県": "Gifu Ken",
    "青森県": "Aomori Ken",
    "大阪府": "Osaka Fu",
    "長野県": "Nagano Ken",
    "大分県": "Oita Ken",
    "三重県": "Mie Ken",
    "広島県": "Hiroshima Ken",
    "北海道": "Hokkai Do",
    "兵庫県": "Hyogo Ken",
    "千葉県": "Chiba Ken",
    "富山県": "Toyama Ken",
    "東京都": "Tokyo To",
    "埼玉県": "Saitama Ken",
    "山口県": "Yamaguchi Ken",
    "福島県": "Fukushima Ken",
    "石川県": "Ishikawa Ken",
    "福井県": "Fukui Ken",
    "愛媛県": "Ehime Ken",
    "奈良県": "Nara Ken",
    "島根県": "Shimane Ken",
    "岩手県": "Iwate Ken",
    "鳥取県": "Tottori Ken",
    "徳島県": "Tokushima Ken",
    "鹿児島県": "Kagoshima Ken",
    "新潟県": "Niigata Ken",
    "高知県": "Kochi Ken",
    "宮崎県": "Miyazaki Ken",
    "神奈川県": "Kanagawa Ken",
    "伊豆諸島": "Tokyo To",
    "小笠原諸島": "Tokyo To",
    "愛媛県宇和海沿岸": "Ehime Ken",
    "大分県豊後水道沿岸": "Oita Ken",
    "鹿児島県東部": "Kagoshima Ken",
    "種子島・屋久島地方": "Kagoshima Ken",
    "沖縄本島地方": "Okinawa Ken",
    "宮古島・八重山地方": "Okinawa Ken"
}

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

# エラー展開
class open_error(nextcord.ui.View):
    def __init__(self, embed, embed2):
        super().__init__(timeout=None)
        self.embed = embed
        self.embed2 = embed2

    @nextcord.ui.button(label="エラーを展開", style=nextcord.ButtonStyle.red)
    async def open_the_error(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.edit_message(embed=self.embed2, view=close_error(self.embed, self.embed2))


class close_error(nextcord.ui.View):
    def __init__(self, embed, embed2):
        super().__init__(timeout=None)
        self.embed = embed
        self.embed2 = embed2

    @nextcord.ui.button(label="エラーを閉じる", style=nextcord.ButtonStyle.red)
    async def close_the_error(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.edit_message(embed=self.embed, view=open_error(self.embed, self.embed2))


# ページボタン
class help_page(nextcord.ui.View):
    def __init__(self, embed, embed2):
        super().__init__(timeout=None)
        self.embed = embed
        self.embed2 = embed2

    @nextcord.ui.button(label="情報", style=nextcord.ButtonStyle.green)
    async def show_info(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.edit_message(embed=self.embed)

    @nextcord.ui.button(label="コマンド", style=nextcord.ButtonStyle.green)
    async def show_commands(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
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
  await eew_channel.send(file=nextcord.File('images/kmoni.png'))
  return

# 津波情報取得
def match_region(area_name, geojson_names):
    if area_name in REGION_MAPPING:
        return REGION_MAPPING[area_name]
    best_match, score = process.extractOne(area_name, geojson_names)
    if score >= 80:
        return best_match
    return None


def get_latest_tsunami_alert(data):
    latest_alert = None
    latest_date = None

    for tsunami in data:
        if tsunami["cancelled"]:
            continue

        created_at = tsunami["created_at"]
        created_at_dt = datetime.strptime(created_at, "%Y/%m/%d %H:%M:%S.%f")

        if latest_date is None or created_at_dt > latest_date:
            latest_alert = tsunami
            latest_date = created_at_dt
    return latest_alert


async def tsunami_info(eew_channel):
    url = "https://api.p2pquake.net/v2/jma/tsunami"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            latest_tsunami = get_latest_tsunami_alert(data)
            if latest_tsunami:
                tsunami_alert_areas = {}
                if not latest_tsunami["cancelled"]:
                    for area in latest_tsunami.get("areas", []):
                        area_name = area["name"]
                        alert_type = area.get("grade")
                        tsunami_alert_areas[area_name] = alert_type

                geojson_names = gdf[GEOJSON_REGION_FIELD].tolist()
                gdf["color"] = "#767676"

                for area_name, alert_type in tsunami_alert_areas.items():
                    matched_region = match_region(area_name, geojson_names)
                    if matched_region:
                        gdf.loc[gdf[GEOJSON_REGION_FIELD] == matched_region, "color"] = ALERT_COLORS.get(alert_type, "white")
                    else:
                        print(f"地域名が一致しませんでした: {area_name}")

                fig, ax = plt.subplots(figsize=(10, 12))
                fig.patch.set_facecolor('#2a2a2a')
                ax.set_facecolor("#2a2a2a")
                gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)
                ax.set_axis_off()

                output_path = "./images/colored_map.png"
                plt.savefig(output_path, bbox_inches="tight", transparent=False, dpi=300)

                tsunami_channel = eew_channel
                if tsunami_channel:
                    embed = Embed(
                        title="津波警報",
                        description="津波警報が発表されている地域の地図です。",
                        color=0xFF0000
                    )
                    file = File(output_path, filename="津波警報地図.png")
                    embed.set_image(url="attachment://津波警報地図.png")
                    await tsunami_channel.send(embed=embed, file=file)
