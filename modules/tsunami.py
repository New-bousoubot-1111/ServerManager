import json
import requests
from colorama import Fore
import geopandas as gpd
import matplotlib.pyplot as plt
from nextcord.ext import commands, tasks
from nextcord import File, Embed
from matplotlib import rcParams
import datetime

# 設定ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

ALERT_COLORS = {"大津波警報": "purple", "津波警報": "red", "津波注意報": "yellow"}
GEOJSON_PATH = "./images/japan.geojson"
GEOJSON_REGION_FIELD = 'nam'

# APIの地域名とGeoJSONの地域名を対応付けるマッピング
REGION_MAPPING = {
    "伊豆諸島": "東京都伊豆諸島",
    "小笠原諸島": "東京都小笠原村",
    "宮崎県": "宮崎県",
    "高知県": "高知県",
    "鹿児島県東部": "鹿児島県",
    "種子島・屋久島地方": "鹿児島県種子島屋久島",
    "宮古島・八重山地方": "沖縄県宮古島市八重山",
    "愛媛県宇和海沿岸": "愛媛県宇和海沿岸",
    "大分県豊後水道沿岸": "大分県豊後水道沿岸",
    "沖縄本島地方": "沖縄本島地方"
}

# GeoJSONデータを読み込む
gdf = gpd.read_file(GEOJSON_PATH)

class tsunami(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|tsunami       |" + Fore.RESET)
        print(Fore.BLUE + "|--------------|" + Fore.RESET)
        self.check_tsunami.start()

    @tasks.loop(minutes=1)
    async def check_tsunami(self):
        url = "https://api.p2pquake.net/v2/jma/tsunami"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"APIリクエストエラー: {e}")
            return

        data = response.json()
        if data:
            tsunami_alert_areas = self.get_tsunami_alert_areas(data)
            # 地域ごとに色付け
            self.update_map_colors(tsunami_alert_areas)
            
            # 地図を描画して保存
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"./images/colored_map_{timestamp}.png"
            self.plot_map(output_path)

            # Discordに送信
            self.send_map_to_discord(output_path)
        else:
            print("津波警報データがありません。")

    def get_tsunami_alert_areas(self, data):
        tsunami_alert_areas = {}
        for tsunami in data:
            if not tsunami["cancelled"]:
                for area in tsunami.get("areas", []):
                    area_name = area["name"]
                    alert_type = area.get("kind", "津波注意報")
                    tsunami_alert_areas[area_name] = alert_type
        return tsunami_alert_areas

    def update_map_colors(self, tsunami_alert_areas):
        # 全ての地域を白に初期化
        gdf["color"] = "#767676"
        for area_name, alert_type in tsunami_alert_areas.items():
            mapped_region = REGION_MAPPING.get(area_name, area_name)
            matched = False
            for index, row in gdf.iterrows():
                region_name = row[GEOJSON_REGION_FIELD]
                if mapped_region in region_name:
                    gdf.loc[index, "color"] = ALERT_COLORS.get(alert_type, "white")
                    matched = True
                    break
            if not matched:
                print(f"未一致地域: {area_name} | REGION_MAPPING: {REGION_MAPPING.get(area_name, 'なし')}")

    def plot_map(self, output_path):
        fig, ax = plt.subplots(figsize=(10, 12))
        fig.patch.set_facecolor('#2a2a2a')
        ax.set_facecolor("#2a2a2a")
        gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=1.5, cmap='viridis')
        ax.set_axis_off()
        plt.savefig(output_path, bbox_inches="tight", transparent=True, dpi=300)

    async def send_map_to_discord(self, output_path):
        tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
        if tsunami_channel:
            embed = Embed(title="津波警報", description="津波警報が発表されている地域の地図です。", color=0xFF0000)
            file = File(output_path, filename="津波警報地図.png")
            embed.set_image(url="attachment://津波警報地図.png")
            await tsunami_channel.send(embed=embed, file=file)

def setup(bot):
    bot.add_cog(tsunami(bot))
