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

    # 投影座標系に変換してバッファ生成
    coastline_gdf = coastline_gdf.to_crs(epsg=3857)  # 投影座標系に変換
    buffer_distance = 0.1  # 5000メートル（5km）のバッファ
    coastline_buffer = coastline_gdf.geometry.buffer(buffer_distance)  # バッファ生成
    print("バッファ生成成功:", coastline_buffer.head())

    # バッファをプロット（CRS変換後）
    coastline_buffer.plot()
    plt.title("Coastline Buffer (EPSG:3857)")
    plt.show()  # バッファを表示

    # 元のCRS（WGS84）に戻す
    coastline_buffer = coastline_buffer.set_crs(epsg=3857).to_crs(epsg=4326)  # CRSを元に戻す
    print("CRSを元に戻しました:", coastline_buffer.crs)

    # 元の座標系でバッファを再度プロット
    coastline_buffer.plot()
    plt.title("Coastline Buffer (EPSG:4326)")
    plt.show()  # 再度、元のCRSで表示

except Exception as e:
    print("海岸線データの処理エラー:", e)
    raise

REGION_MAPPING = {
    "沖縄本島地方": "沖縄県",
    "宮古島・八重山地方": "沖縄県",
    "小笠原諸島": "東京都",
    "伊豆諸島": "東京都"
}

# 海岸線データを修復する関数
def fix_geometry(gdf):
    """GeoDataFrameのジオメトリを修復"""
    gdf["geometry"] = gdf["geometry"].buffer(0)
    return gdf

# 海岸線データを修正
print("海岸線データの修復中...")
coastline_gdf = fix_geometry(coastline_gdf)

# バッファを作成
print("バッファを作成中...")
buffer_distance = 5000  # 5km
coastline_buffer = coastline_gdf.geometry.buffer(buffer_distance)

# バッファを修復
print("バッファの修復中...")
coastline_buffer = coastline_buffer.buffer(0)

# CRSを元に戻す
coastline_buffer = coastline_buffer.to_crs(epsg=4326)
print(gdf.crs)  # 地域データのCRS
print(coastline_buffer.crs)  # 海岸線バッファのCRS

def match_region(area_name, geojson_names):
    """地域名をGeoJSONデータと一致させる"""
    if area_name in geojson_names:
        return area_name
    if area_name in REGION_MAPPING:
        return REGION_MAPPING[area_name]
    best_match, score = process.extractOne(area_name, geojson_names)
    return best_match if score >= 80 else None

def is_near_coastline(region_geometry):
    """地域が海岸線のバッファ領域と交差するかを判定する"""
    return coastline_buffer.intersects(region_geometry).any()  # 修正

def create_embed(data):
    alert_levels = {
        "Advisory": {"title": "大津波警報", "color": 0x800080},  # 紫
        "Warning": {"title": "津波警報", "color": 0xff0000},    # 赤
        "Watch": {"title": "津波注意報", "color": 0xffff00}       # 黄
    }
    embed_title = "津波情報"
    embed_color = 0x00FF00

    levels_in_data = [area.get("grade") for area in data.get("areas", [])]
    for level in ["Advisory", "Warning", "Watch"]:
        if level in levels_in_data:
            embed_title = alert_levels[level]["title"]
            embed_color = alert_levels[level]["color"]
            break

    embed = Embed(title=embed_title, color=embed_color)
    tsunami_time = parser.parse(data.get("time", "不明"))
    formatted_time = tsunami_time.strftime('%Y年%m月%d日 %H時%M分')

    if data.get("areas"):
        embed.description = f"{embed_title}が発表されました\n安全な場所に避難してください"
        embed.add_field(name="発表時刻", value=formatted_time, inline=False)

    for area in data.get("areas", []):
        area_name = area["name"]
        first_height = area.get("firstHeight", {})
        maxHeight = area.get("maxHeight", {})
        condition = first_height.get("condition", "")
        description = maxHeight.get("description", "不明")
        arrival_time = first_height.get("arrivalTime", "不明")

        if arrival_time != "不明":
            try:
                arrival_time = parser.parse(arrival_time).strftime('%H時%M分')
                embed.add_field(
                    name=area_name,
                    value=f"到達予想時刻: {arrival_time}\n予想高さ: {description}\n{condition}",
                    inline=False
                )
            except ValueError:
                pass
        elif arrival_time == "不明":
            embed.add_field(
                name=area_name,
                value=f"予想高さ: {description}\n{condition}",
                inline=False
            )
    tsunami_time2 = parser.parse(data.get("time", "不明"))
    formatted_time2 = tsunami_time2.strftime('%H時%M分')
    if not data.get("areas"):
        embed.add_field(
            name=f"{formatted_time2}頃に津波警報、注意報等が解除されました。",
            value="念のため、今後の情報に気をつけてください。",
            inline=False
        )
    return embed

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
        ax.set_xlim([-180, 180])  # 経度の範囲
        ax.set_ylim([-90, 90])    # 緯度の範囲
        ax.set_aspect('auto')
        print(coastline_buffer_gdf.is_valid)
        print(gdf.is_valid)


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
