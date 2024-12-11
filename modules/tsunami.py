import json
import requests
import geopandas as gpd
import matplotlib.pyplot as plt
from nextcord.ext import commands, tasks
from nextcord import File
from colorama import Fore

# configファイルの読み込み
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

class tsunami(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|tasks         |" + Fore.RESET)
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

                # 地図の描画
                fig, ax = plt.subplots(figsize=(10, 12))
                gdf["color"] = "white"  # デフォルトの色

                # 一致確認用のログ
                unmatched_areas = []

                for index, row in gdf.iterrows():
                    matched = False
                    for area_name, alert_type in tsunami_alert_areas.items():
                        if area_name in row["NAM"]:  # 地域名が一致
                            gdf.at[index, "color"] = ALERT_COLORS.get(alert_type, "white")
                            matched = True
                    if not matched:
                        unmatched_areas.append(row["NAM"])

                # 未一致地域を出力 (デバッグ用)
                if unmatched_areas:
                    print(f"一致しなかった地域: {unmatched_areas}")

                # 地域を描画
                gdf.plot(ax=ax, color=gdf["color"], edgecolor="black")

                # 凡例とタイトルの追加
                plt.title("津波情報", fontsize=16)
                plt.annotate("発表日時: 気象庁", (0, 0), xycoords="axes fraction", fontsize=10)

                # 画像を保存
                output_path = "./images/colored_map.png"
                plt.savefig(output_path)
                plt.show()  # ローカルで地図を確認 (必要に応じて)

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