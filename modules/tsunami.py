import json
import requests
from colorama import Fore
import geopandas as gpd
import matplotlib.pyplot as plt
from fuzzywuzzy import process
from nextcord.ext import commands, tasks
from nextcord import File, Embed
from datetime import datetime
from dateutil import parser

# 設定ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

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
    "伊豆諸島": "Tokyo To",  # 伊豆諸島を東京とマッピング
    "小笠原諸島": "Tokyo To",  # 小笠原諸島を東京とマッピング
    "愛媛県宇和海沿岸": "Ehime Ken",
    "大分県豊後水道沿岸": "Oita Ken",
    "鹿児島県東部": "Kagoshima Ken",
    "種子島・屋久島地方": "Kagoshima Ken",
    "沖縄本島地方": "Okinawa Ken",
    "宮古島・八重山地方": "Okinawa Ken"
}

def match_region(area_name, geojson_names):
    if area_name in REGION_MAPPING:
        return REGION_MAPPING[area_name]
    best_match, score = process.extractOne(area_name, geojson_names)
    if score >= 80:
        return best_match
    return None

class tsunami(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tsunami_sent_ids = set()
        self.tsunami_cache_file = 'json/tsunami_id.json'
        self.load_tsunami_sent_ids()

    def load_tsunami_sent_ids(self):
        try:
            with open(self.tsunami_cache_file, "r") as f:
                self.tsunami_sent_ids = set(json.load(f))
        except FileNotFoundError:
            self.tsunami_sent_ids = set()

    def save_tsunami_sent_ids(self):
        with open(self.tsunami_cache_file, "w") as f:
            json.dump(list(self.tsunami_sent_ids), f)

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|tsunami       |" + Fore.RESET)
        print(Fore.BLUE + "|--------------|" + Fore.RESET)
        self.check_tsunami.start()

    @tasks.loop(minutes=1)
    async def check_tsunami(self):
        url = "https://api.p2pquake.net/v2/jma/tsunami"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                latest_tsunami = max(data, key=lambda x: parser.parse(x["time"]))
                tsunami_id = latest_tsunami.get("id")
                if not tsunami_id or tsunami_id in self.tsunami_sent_ids:
                    return

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
                plt.close(fig)

                tsunami_time = parser.parse(latest_tsunami.get("time", "不明"))
                formatted_time = tsunami_time.strftime('%Y年%m月%d日 %H時%M分')
                embed = Embed(
                    title="津波警報",
                    description="最新の津波警報情報です。安全な場所に避難してください。",
                    color=0xFF0000
                )
                embed.add_field(name="発表時刻", value=formatted_time)
                for area_name, alert_type in tsunami_alert_areas.items():
                    embed.add_field(
                        name=area_name,
                        value=f"警報タイプ: {alert_type}",
                        inline=False
                    )

                tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
                if tsunami_channel:
                    file = File(output_path, filename="津波警報地図.png")
                    embed.set_image(url="attachment://津波警報地図.png")
                    await tsunami_channel.send(embed=embed, file=file)

                self.tsunami_sent_ids.add(tsunami_id)
                self.save_tsunami_sent_ids()
            else:
                print("津波警報データがありません。")
        else:
            print("津波データの取得に失敗しました。")

def setup(bot):
    bot.add_cog(tsunami(bot))
