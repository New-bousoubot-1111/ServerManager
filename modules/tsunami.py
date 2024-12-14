import json
import requests
from colorama import Fore
from nextcord.ext import commands, tasks
from nextcord import File, Embed
from datetime import datetime
from dateutil import parser
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from fuzzywuzzy import process
import os

# 設定ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

ALERT_COLORS = {"Advisory": "purple", "Warning": "red", "Watch": "yellow"}
GEOJSON_PATH = "./images/japan.geojson"  # 日本のGeoJSONファイルのパス
COASTLINE_PATH = "./images/coastline.geojson"  # 海岸線のGeoJSONファイルのパス
GEOJSON_REGION_FIELD = 'nam_ja'

# GeoJSONデータの読み込み
print("GeoJSONファイルの読み込み中...")
try:
    gdf = gpd.read_file(GEOJSON_PATH)
    coastline_gdf = gpd.read_file(COASTLINE_PATH)
    print("GeoJSONデータ:", gdf.head())
    print("海岸線データ:", coastline_gdf.head())
except Exception as e:
    print("GeoJSONファイルの読み込みエラー:", e)
    raise

# 海岸線データの処理
print("海岸線データの処理中...")
try:
    if coastline_gdf.crs is None:
        print("CRSが設定されていません。WGS84に設定します。")
        coastline_gdf.set_crs(epsg=4326, inplace=True)
    print("元のCRS:", coastline_gdf.crs)

    # 空のジオメトリを削除
    coastline_gdf = coastline_gdf[~coastline_gdf.is_empty]

    # 座標系をEPSG:3857（Webメルカトル）に変換してバッファ生成
    coastline_gdf = coastline_gdf.to_crs(epsg=3857)  # 投影座標系（Web Mercator）
    buffer_distance = 5000  # 5000メートル（5km）のバッファ
    coastline_buffer = coastline_gdf.geometry.buffer(buffer_distance)
    print("バッファ生成成功:", coastline_buffer.head())

    # 元のCRS（WGS84）に戻す
    coastline_buffer = gpd.GeoSeries(coastline_buffer).set_crs(epsg=3857).to_crs(epsg=4326)
    print("CRSを元に戻しました:", coastline_buffer.crs)
except Exception as e:
    print("海岸線データの処理エラー:", e)
    raise

# 地図生成関数
def generate_map(tsunami_alert_areas):
    """津波警報地図を生成し、ローカルパスを返す"""
    print("地図生成中...")
    geojson_names = gdf[GEOJSON_REGION_FIELD].tolist()
    gdf["color"] = "#767676"  # 全地域を灰色に設定

    try:
        # バッファとの交差判定（ログを追加）
        print("海岸線との交差判定を実施中...")
        for idx, region in gdf.iterrows():
            region_geometry = region.geometry
            if coastline_buffer.intersects(region_geometry).any():
                gdf.at[idx, "color"] = "blue"  # 海岸沿いは青色

        # 津波警報エリアの色設定
        print("津波警報エリアの色設定を実施中...")
        for area_name, alert_type in tsunami_alert_areas.items():
            matched_region = process.extractOne(area_name, geojson_names)[0]
            print(f"地域名: {area_name}, マッチ結果: {matched_region}")
            if matched_region:
                gdf.loc[gdf[GEOJSON_REGION_FIELD] == matched_region, "color"] = ALERT_COLORS.get(alert_type, "white")

        # 地図の描画
        print("地図を描画中...")
        fig, ax = plt.subplots(figsize=(15, 18))
        fig.patch.set_facecolor('#2a2a2a')
        ax.set_facecolor("#2a2a2a")
        ax.set_xlim([122, 153])  # 東経122度～153度（日本全体をカバー）
        ax.set_ylim([20, 46])    # 北緯20度～46度（南西諸島から北海道まで）

        # 海岸線を描画（色を指定）
        coastline_gdf.plot(ax=ax, color="blue", edgecolor="black", linewidth=2)

        # その他の地域を描画
        gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)

        # 軸非表示
        ax.set_axis_off()

        # アスペクト比の設定を自動に変更
        ax.set_aspect('auto')

        # 出力パスに保存
        output_path = "images/tsunami.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)  # ディレクトリが存在しない場合は作成
        plt.savefig(output_path, bbox_inches="tight", transparent=False, dpi=300)
        plt.close()

        print(f"地図が正常に保存されました: {output_path}")
        return output_path
    except Exception as e:
        print(f"地図生成エラー: {e}")
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
            if not data:
                print("津波データが空です。")
                return

            latest_date = max(parser.parse(tsunami["time"]).date() for tsunami in data)
            filtered_tsunamis = [
                tsunami for tsunami in data
                if parser.parse(tsunami["time"]).date() == latest_date
            ]
            filtered_tsunamis.sort(key=lambda tsunami: parser.parse(tsunami["time"]))

            tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
            if not tsunami_channel:
                print("送信先チャンネルが見つかりません。")
                return

            for tsunami in filtered_tsunamis:
                tsunami_id = tsunami.get("id")
                if not tsunami_id or tsunami_id in self.tsunami_sent_ids:
                    continue
                embed = create_embed(tsunami)
                tsunami_alert_areas = {
                    area["name"]: area.get("grade") for area in tsunami.get("areas", [])
                }

                if tsunami_alert_areas:
                    map_path = generate_map(tsunami_alert_areas)
                    embed.set_image(url="attachment://tsunami.png")
                    with open(map_path, "rb") as file:
                        discord_file = File(file, filename="tsunami.png")
                        await tsunami_channel.send(embed=embed, file=discord_file)
                else:
                    await tsunami_channel.send(embed=embed)

                self.tsunami_sent_ids.add(tsunami_id)
                self.save_tsunami_sent_ids()

def setup(bot):
    bot.add_cog(tsunami(bot))
