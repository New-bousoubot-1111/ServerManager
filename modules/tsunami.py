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

# GeoJSON ファイルのカラム名を確認
print("GeoJSON columns:", gdf.columns)

# 修正したカラム名を使って、地域名を取得
# 例: カラム名が 'name' の場合、以下のように変更
GEOJSON_REGION_FIELD = 'name'  # 正しいフィールド名に変更

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

                # 地図の描画
                fig, ax = plt.subplots(figsize=(10, 12))
                gdf["color"] = "white"  # デフォルトの色

                # 地域を描画する際に部分一致でチェック
                for index, row in gdf.iterrows():
                    matched = False
                    for area_name, alert_type in tsunami_alert_areas.items():
                        # 地域名が部分一致する場合に対応
                        if area_name in row[GEOJSON_REGION_FIELD]:
                            matched = True
                            print(f"Matched: {area_name} -> {row[GEOJSON_REGION_FIELD]}")  # デバッグ用
                            gdf.at[index, "color"] = ALERT_COLORS.get(alert_type, "white")
                    if not matched:
                        # 未一致地域をデバッグ出力
                        print(f"Unmatched GeoJSON area: {row[GEOJSON_REGION_FIELD]}")

                # 地域を描画
                gdf.plot(ax=ax, color=gdf["color"], edgecolor="black")
                # 画像を保存
                output_path = "./images/colored_map.png"
                plt.savefig(output_path)

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
