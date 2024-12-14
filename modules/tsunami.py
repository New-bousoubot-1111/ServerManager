import json
import requests
from colorama import Fore
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from fuzzywuzzy import process
from nextcord.ext import commands, tasks
from nextcord import File, Embed
from datetime import datetime
from dateutil import parser
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
    print(coastline_gdf.geometry)
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

    # CRSをEPSG:3857に変換
    coastline_gdf = coastline_gdf.to_crs(epsg=3857)  # 投影座標系に変換
    print("海岸線データのCRSをEPSG:3857に変換しました:", coastline_gdf.crs)

    # バッファ生成
    buffer_distance = 5000  # 5km
    coastline_buffer = coastline_gdf.geometry.buffer(buffer_distance)  # バッファ生成
    print("バッファ生成成功:", coastline_buffer.head())

    # バッファをプロット（EPSG:3857座標系）
    coastline_buffer.plot()
    plt.title("Coastline Buffer (EPSG:3857)")
    plt.show()

    # バッファをEPSG:3857座標系で保持
    coastline_buffer = coastline_buffer.set_crs(epsg=3857)
    print("バッファの座標系をEPSG:3857に設定:", coastline_buffer.crs)

except Exception as e:
    print("海岸線データの処理エラー:", e)
    raise

def generate_map(tsunami_alert_areas):
    """津波警報地図を生成し、ローカルパスを返す"""
    print("地図生成中...")
    geojson_names = gdf[GEOJSON_REGION_FIELD].tolist()
    gdf["color"] = "#767676"  # 全地域を灰色に設定

    try:
        # 海岸線バッファをGeoDataFrameに変換
        print("海岸線バッファの処理中...")
        coastline_buffer_gdf = gpd.GeoDataFrame(geometry=coastline_buffer, crs=gdf.crs)

        # 海岸線バッファと交差する地域に色を付ける
        print("海岸線バッファとの交差判定を実施中...")
        for idx, region in gdf.iterrows():
            region_geometry = region.geometry
            if coastline_buffer_gdf.intersects(region_geometry).any():
                gdf.at[idx, "color"] = "blue"  # 海岸沿いは青色に設定

        # 津波警報エリアの色設定
        print("津波警報エリアの色設定を実施中...")
        for area_name, alert_type in tsunami_alert_areas.items():
            matched_region = match_region(area_name, geojson_names)
            print(f"地域名: {area_name}, マッチ結果: {matched_region}")
            if matched_region:
                gdf.loc[gdf[GEOJSON_REGION_FIELD] == matched_region, "color"] = ALERT_COLORS.get(alert_type, "white")

        # 地図の描画
        print("地図を描画中...")
        fig, ax = plt.subplots(figsize=(15, 18))
        fig.patch.set_facecolor('#2a2a2a')
        ax.set_facecolor("#2a2a2a")

        # すべてのGeoDataFrameをEPSG:3857に変換
        gdf = gdf.to_crs(epsg=3857)
        coastline_buffer_gdf = coastline_buffer_gdf.to_crs(epsg=3857)

        # 描画範囲を設定 (投影法がEPSG:3857の場合)
        ax.set_xlim([-20000000, 20000000])  # Web Mercatorの範囲に合わせた設定
        ax.set_ylim([-10000000, 10000000])

        ax.set_aspect('auto')  # アスペクト比を自動調整

        # 海岸線バッファを背景に描画
        coastline_buffer_gdf.plot(ax=ax, color="blue", alpha=0.5, edgecolor="none", linewidth=0, label="Coastline Buffer")

        # 津波警報地域を描画
        gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)

        # 軸非表示
        ax.set_axis_off()
        plt.legend()

        # 出力パスに保存
        output_path = "images/tsunami.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, bbox_inches="tight", transparent=False, dpi=300)
        plt.close()
        print(f"地図が正常に保存されました: {output_path}")
        return output_path

    except Exception as e:
        print("地図生成エラー:", e)
        raise

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
