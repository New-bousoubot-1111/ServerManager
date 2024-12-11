import json
import requests
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from nextcord.ext import commands, tasks
from nextcord import File
from colorama import Fore

# 設定ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

# 津波警報の種類に対応する色
ALERT_COLORS = {
    "大津波警報": "purple",
    "津波警報": "red",
    "津波注意報": "yellow"
}

# GeoJSON データの読み込み
GEOJSON_PATH = "./images/japan.geojson"  # 日本の地域データ (都道府県や市区町村の境界)
gdf = gpd.read_file(GEOJSON_PATH)

# GeoJSON ファイルのカラム名を確認
print("GeoJSON columns:", gdf.columns)

# 修正したカラム名を使って、地域名を取得
GEOJSON_REGION_FIELD = 'nam'  # 'nam' カラムを使用

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
        url = "https://api.p2pquake.net/v2/jma/tsunami"  # 津波 API
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                tsunami_alert_areas = {}  # 地域ごとの警報種類を保存

                # API データ処理
                for tsunami in data:
                    if not tsunami["cancelled"]:  # 発表中の警報のみ処理
                        for area in tsunami.get("areas", []):
                            area_name = area["name"]
                            alert_type = area.get("kind", "津波注意報")
                            tsunami_alert_areas[area_name] = alert_type

                # 地図の描画準備
                gdf["color"] = "white"  # デフォルトの色

                # 地域を描画する際に部分一致でチェック
                for index, row in gdf.iterrows():
                    for area_name, alert_type in tsunami_alert_areas.items():
                        # 地域名が部分一致する場合に対応
                        if area_name in row[GEOJSON_REGION_FIELD]:
                            gdf.at[index, "color"] = ALERT_COLORS.get(alert_type, "white")
                            break

                # 未一致地域をデバッグ出力
                for area_name in tsunami_alert_areas.keys():
                    if not any(area_name in region for region in gdf[GEOJSON_REGION_FIELD]):
                        print(f"未一致地域: {area_name}")

                # 地図描画
                fig, ax = plt.subplots(figsize=(10, 12))
                ax.set_facecolor("black")  # 背景を黒に設定
                gdf.plot(ax=ax, color=gdf["color"], edgecolor="gray")  # 色と境界線を設定

                # タイトルと凡例の追加
                plt.title("津波情報", fontsize=18, color="white")
                patches = [
                    mpatches.Patch(color="purple", label="大津波警報"),
                    mpatches.Patch(color="red", label="津波警報"),
                    mpatches.Patch(color="yellow", label="津波注意報")
                ]
                plt.legend(handles=patches, loc="upper left", fontsize=12, frameon=False, title="津波情報", title_fontsize=14)

                # 発表日時を追加
                plt.annotate(
                    "1月1日 16時22分 気象庁発表",
                    xy=(0.5, 1.05),
                    xycoords="axes fraction",
                    fontsize=10,
                    ha="center",
                    color="white"
                )

                # 画像を保存
                output_path = "./images/colored_map.png"
                plt.savefig(output_path, bbox_inches="tight", facecolor=ax.figure.get_facecolor())

                # Discord チャンネルに送信
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
