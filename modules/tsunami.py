import json
import requests
from colorama import Fore
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from nextcord.ext import commands, tasks
from nextcord import File

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
    "宮古島・八重山地方": "沖縄県宮古島市八重山"
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
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                tsunami_alert_areas = {}
                for tsunami in data:
                    if not tsunami["cancelled"]:
                        for area in tsunami.get("areas", []):
                            area_name = area["name"]
                            alert_type = area.get("kind", "津波注意報")
                            tsunami_alert_areas[area_name] = alert_type
                # 全ての地域を白に初期化
                gdf["color"] = "#767676"
                # 地域ごとに色付け
                for area_name, alert_type in tsunami_alert_areas.items():
                    matched = False
                    for index, row in gdf.iterrows():
                        region_name = row[GEOJSON_REGION_FIELD]
                        if area_name in region_name or REGION_MAPPING.get(area_name, "") in region_name:
                            gdf.at[index, "color"] = ALERT_COLORS.get(alert_type, "white")
                            matched = True
                            break
                    if not matched:
                        print(f"未一致地域: {area_name} | REGION_MAPPING: {REGION_MAPPING.get(area_name, 'なし')}")

                # 地図を描画
                fig, ax = plt.subplots(figsize=(15, 18))  # サイズを大きく
                fig.patch.set_facecolor('#2e2e2e')  # 全体の背景色
                ax.set_facecolor("#2e2e2e")  # 地図の背景色を薄い灰色に設定

                # 地図描画
                gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)

                # 軸を非表示にする
                ax.set_axis_off()

                # タイトル
                plt.title("津波情報", fontsize=18, color="white")

                # 凡例
                patches = [
                    mpatches.Patch(color="purple", label="大津波警報"),
                    mpatches.Patch(color="red", label="津波警報"),
                    mpatches.Patch(color="yellow", label="津波注意報")
                ]
                plt.legend(handles=patches, loc="upper left", fontsize=12, frameon=False, title="津波情報", title_fontsize=14)

                # 画像保存（高解像度）
                output_path = "./images/colored_map.png"
                plt.savefig(output_path, bbox_inches="tight", transparent=True, facecolor=ax.figure.get_facecolor(), dpi=300)

                # Discordに送信
                tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
                if tsunami_channel:
                    await tsunami_channel.send(
                        "津波警報が発表されている地域の地図です。",
                        file=File(output_path)
                    )
            else:
                print("津波警報データがありません。")
        else:
            print("津波データの取得に失敗しました。")

def setup(bot):
    bot.add_cog(tsunami(bot))
