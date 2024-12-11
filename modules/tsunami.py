import os
import json
import requests
from colorama import Fore
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from nextcord.ext import commands, tasks
from nextcord import File
from matplotlib import rcParams
from matplotlib import font_manager as fm

# フォントファイルのパスを指定
FONT_PATH = "./json/NotoSansJP-Black.ttf"
if not os.path.exists(FONT_PATH):
    raise FileNotFoundError(f"フォントファイルが見つかりません: {FONT_PATH}")
font_prop = fm.FontProperties(fname=FONT_PATH)
rcParams['font.family'] = font_prop.get_name()

# 設定ファイルの読み込み
CONFIG_PATH = 'json/config.json'
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"設定ファイルが見つかりません: {CONFIG_PATH}")
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

ALERT_COLORS = {"大津波警報": "purple", "津波警報": "red", "津波注意報": "yellow"}
GEOJSON_PATH = "./images/japan.geojson"
if not os.path.exists(GEOJSON_PATH):
    raise FileNotFoundError(f"GEOJSONファイルが見つかりません: {GEOJSON_PATH}")

GEOJSON_REGION_FIELD = 'nam'
REGION_MAPPING = {
    "伊豆諸島": "東京都伊豆諸島",
    "小笠原諸島": "東京都小笠原村",
    "宮崎県": "宮崎県",
    "愛媛県宇和海沿岸": "愛媛県",
    "高知県": "高知県",
    "大分県豊後水道沿岸": "大分県",
    "鹿児島県東部": "鹿児島県",
    "種子島・屋久島地方": "鹿児島県種子島屋久島",
    "沖縄本島地方": "沖縄県",
    "宮古島・八重山地方": "沖縄県宮古島市"
}
gdf = gpd.read_file(GEOJSON_PATH)

class tsunami(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|tsunami       |" + Fore.RESET)
        print(Fore.BLUE + "|--------------|" + Fore.RESET)
        if not self.check_tsunami.is_running():
            self.check_tsunami.start()

    @tasks.loop(minutes=1)
    async def check_tsunami(self):
        url = "https://api.p2pquake.net/v2/jma/tsunami"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"津波データの取得に失敗しました: {e}")
            return

        data = response.json()
        if not data:
            print("津波警報データがありません。")
            return

        tsunami_alert_areas = {}
        for tsunami in data:
            if not tsunami["cancelled"]:
                for area in tsunami.get("areas", []):
                    area_name = area["name"]
                    alert_type = area.get("kind", "津波注意報")
                    tsunami_alert_areas[area_name] = alert_type

        gdf["color"] = "white"
        unmatched_areas = []
        for area_name, alert_type in tsunami_alert_areas.items():
            matched = False
            for index, row in gdf.iterrows():
                region_name = row[GEOJSON_REGION_FIELD]
                if area_name in region_name or REGION_MAPPING.get(area_name, "") in region_name:
                    gdf.at[index, "color"] = ALERT_COLORS.get(alert_type, "white")
                    matched = True
                    break
            if not matched:
                unmatched_areas.append(area_name)

        if unmatched_areas:
            with open("./unmatched_areas.log", "w") as f:
                f.write("\n".join(unmatched_areas))
            print(f"未一致地域: {unmatched_areas}")

        fig, ax = plt.subplots(figsize=(10, 12))
        ax.set_facecolor("black")
        gdf.plot(ax=ax, color=gdf["color"], edgecolor="gray")

        plt.title("津波情報", fontsize=18, color="white")
        patches = [
            mpatches.Patch(color="purple", label="大津波警報"),
            mpatches.Patch(color="red", label="津波警報"),
            mpatches.Patch(color="yellow", label="津波注意報")
        ]
        plt.legend(handles=patches, loc="upper left", fontsize=12, frameon=False, title="津波情報", title_fontsize=14)

        plt.annotate(
            "最新の気象庁発表",
            xy=(0.5, 1.05),
            xycoords="axes fraction",
            fontsize=10,
            ha="center",
            color="white"
        )

        output_path = "./images/japan.geojson"
        plt.savefig(output_path, bbox_inches="tight", facecolor=ax.figure.get_facecolor())
        plt.close(fig)

        tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
        if tsunami_channel:
            await tsunami_channel.send(
                "津波警報が発表されている地域の地図です。",
                file=File(output_path)
            )

def setup(bot):
    bot.add_cog(tsunami(bot))
