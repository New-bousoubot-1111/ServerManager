import json
import requests
from colorama import Fore
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import rcParams
import re
from fuzzywuzzy import process
from nextcord.ext import commands, tasks
from nextcord import File, Embed

# 設定ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

ALERT_COLORS = {"大津波警報": "purple", "津波警報": "red", "津波注意報": "yellow"}
GEOJSON_PATH = "./images/japan.geojson"
GEOJSON_REGION_FIELD = 'nam'

# GeoJSONデータを読み込む
gdf = gpd.read_file(GEOJSON_PATH)


def preprocess_area_name(area_name):
    # 地名を正規化（例: 「沿岸」「地方」を削除）
    area_name = re.sub(r"(沿岸|地方)", "", area_name)
    return area_name
# 修正例: 正規化を組み合わせる
def match_region(area_name, geojson_names):
    area_name = preprocess_area_name(area_name)  # 正規化
    best_match, score = process.extractOne(area_name, geojson_names)
    if score >= 70:
        return best_match
    return None


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

                # GeoJSONの地域名リストを取得
                geojson_names = gdf[GEOJSON_REGION_FIELD].tolist()
                
                # 全ての地域を灰色で初期化
                gdf["color"] = "#767676"

                # 地域ごとに色付け
                for area_name, alert_type in tsunami_alert_areas.items():
                    matched_region = match_region(area_name, geojson_names)
                    if matched_region:
                        gdf.loc[gdf[GEOJSON_REGION_FIELD] == matched_region, "color"] = ALERT_COLORS.get(alert_type, "white")
                    else:
                        print(f"地域名が一致しませんでした: {area_name}")

                # 地図を描画
                fig, ax = plt.subplots(figsize=(10, 12))
                fig.patch.set_facecolor('#2a2a2a')  # 地図全体の背景色を薄い灰色に設定
                ax.set_facecolor("#2a2a2a")
                gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)
                ax.set_axis_off()

                # 地図を保存
                output_path = "./images/colored_map.png"
                plt.savefig(output_path, bbox_inches="tight", transparent=False, dpi=300)

                # Discordに送信
                tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
                if tsunami_channel:
                    embed = Embed(
                        title="津波警報",
                        description="津波警報が発表されている地域の地図です。",
                        color=0xFF0000
                    )
                    file = File(output_path, filename="津波警報地図.png")
                    embed.set_image(url="attachment://津波警報地図.png")
                    await tsunami_channel.send(embed=embed, file=file)
            else:
                print("津波警報データがありません。")
        else:
            print("津波データの取得に失敗しました。")

def setup(bot):
    bot.add_cog(tsunami(bot))
