import json
import requests
from colorama import Fore
import geopandas as gpd
import matplotlib.pyplot as plt
from nextcord.ext import commands, tasks
from nextcord import File, Embed
from matplotlib import rcParams

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
    "愛媛県宇和海沿岸": "愛媛県宇和海沿岸",  # 追加
    "大分県豊後水道沿岸": "大分県豊後水道沿岸",  # 追加
    "沖縄本島地方": "沖縄本島地方"  # 追加
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
                    # REGION_MAPPING を使って地域名を対応付ける
                    mapped_region = REGION_MAPPING.get(area_name, area_name)
                    for index, row in gdf.iterrows():
                        region_name = row[GEOJSON_REGION_FIELD]
                        # 部分一致でマッチさせる
                        if mapped_region in region_name:  
                            gdf.at[index, "color"] = ALERT_COLORS.get(alert_type, "white")
                            matched = True
                            break
                    if not matched:
                        # ここでログに未一致の地域名を出力
                        print(f"未一致地域: {area_name} | REGION_MAPPING: {REGION_MAPPING.get(area_name, 'なし')} | 地域名: {region_name}")

                # 地図を描画
                fig, ax = plt.subplots(figsize=(10, 12))  # サイズを大きく
                fig.patch.set_facecolor('#2a2a2a')  # 全体の背景色
                ax.set_facecolor("#2a2a2a")  # 地図の背景色を薄い灰色に設定
                # 地図描画
                gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)
                # 軸を非表示にする
                ax.set_axis_off()
                # 画像保存（高解像度）
                output_path = "./images/colored_map.png"
                plt.savefig(output_path, bbox_inches="tight", transparent=True, facecolor=ax.figure.get_facecolor(), dpi=300)
                # Discordに送信
                tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
                if tsunami_channel:
                    # Embedを作成
                    embed = Embed(
                        title="津波警報",
                        description="津波警報が発表されている地域の地図です。",
                        color=0xFF0000  # 警告色を赤に設定
                    )
                    # 添付ファイルとして画像を追加
                    file = File(output_path, filename="津波警報地図.png")
                    embed.set_image(url="attachment://津波警報地図.png")  # 添付ファイル名を指定
                    # メッセージ送信
                    await tsunami_channel.send(embed=embed, file=file)
            else:
                print("津波警報データがありません。")
        else:
            print("津波データの取得に失敗しました。")

def setup(bot):
    bot.add_cog(tsunami(bot))
