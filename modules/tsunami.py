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
from PIL import Image, ImageDraw, ImageFont

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

    # 投影座標系に変換してバッファ生成
    coastline_gdf = coastline_gdf.to_crs(epsg=3857)
    buffer_distance = 5000  # 5000メートル（5km）のバッファ
    coastline_buffer = coastline_gdf.geometry.buffer(buffer_distance)
    print("バッファ生成成功:", coastline_buffer.head())

    # 元のCRS（WGS84）に戻す
    coastline_buffer = gpd.GeoSeries(coastline_buffer).set_crs(epsg=3857).to_crs(epsg=4326)
    print("CRSを元に戻しました:", coastline_buffer.crs)
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

def match_region(area_name, geojson_names):
    """地域名をGeoJSONデータと一致させる"""
    if area_name in geojson_names:
        return area_name
    if area_name in REGION_MAPPING:
        return REGION_MAPPING[area_name]
    best_match, score = process.extractOne(area_name, geojson_names)
    return best_match if score >= 80 else None

def is_near_coastline(region):
    """地域が海岸線のバッファ領域と交差するかを判定する"""
    return coastline_buffer.intersects(region).any()

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

def color_adjacent_coastlines(tsunami_alert_regions, coastline_gdf, alert_colors):
    """
    津波警報エリアに隣接する海岸線を特定し、警報レベルに応じて色を設定する関数
    :param tsunami_alert_regions: 津波警報が発令されている地域のジオメトリ一覧
    :param coastline_gdf: 海岸線データのGeoDataFrame
    :param alert_colors: 警報レベルに対応する色の辞書
    """
    for idx, coast in coastline_gdf.iterrows():
        for region, alert_type in tsunami_alert_regions:
            # 海岸線が津波警報地域に接しているか交差している場合
            if coast.geometry.intersects(region) or coast.geometry.touches(region):
                coastline_gdf.at[idx, "color"] = alert_colors.get(alert_type, "#ffffff")
                break

def add_text_image(image_path, output_path, text, font_path="json/NotoSansJP-Regular.ttf"):
    """
    画像の左上に枠線・テキスト・凡例の色付き線を追加する
    :param image_path: 入力画像のパス
    :param output_path: 出力画像のパス
    :param text: 描画するテキスト
    :param font_path: 日本語フォントのパス
    """
    try:
        # 画像を開く
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)

        # テキスト枠の設定
        box_x, box_y = 20, 20  # 左上からの座標
        box_width, box_height = 400, 180  # 枠のサイズ
        border_color = (255, 0, 0)  # 赤色
        border_width = 4

        # 枠を描画
        draw.rectangle(
            [(box_x, box_y), (box_x + box_width, box_y + box_height)],
            outline=border_color, width=border_width, fill=(255, 255, 255)
        )

        # テキスト描画の設定
        font_size = 24
        font = ImageFont.truetype(font_path, font_size)
        text_color = (0, 0, 0)  # 黒色
        text_position = (box_x + 10, box_y + 10)

        # テキストの描画
        draw.text(text_position, text, fill=text_color, font=font)

        # 凡例の色付き線を描画
        legend_x, legend_y = box_x + 10, box_y + 80
        legend_gap = 40

        # 大津波警報（紫色）
        draw.line([(legend_x, legend_y), (legend_x + 50, legend_y)], fill=(128, 0, 128), width=8)
        draw.text((legend_x + 60, legend_y - 10), "大津波警報", fill=text_color, font=font)

        # 津波警報（赤色）
        draw.line([(legend_x, legend_y + legend_gap), (legend_x + 50, legend_y + legend_gap)], fill=(255, 0, 0), width=8)
        draw.text((legend_x + 60, legend_y + legend_gap - 10), "津波警報", fill=text_color, font=font)

        # 津波注意報（黄色）
        draw.line([(legend_x, legend_y + 2 * legend_gap), (legend_x + 50, legend_y + 2 * legend_gap)], fill=(255, 255, 0), width=8)
        draw.text((legend_x + 60, legend_y + 2 * legend_gap - 10), "津波注意報", fill=text_color, font=font)

        # 画像を保存
        image.save(output_path)
        print(f"テキストと凡例を追加した画像が保存されました: {output_path}")

    except Exception as e:
        print("エラーが発生しました:", e)
        raise

def add_text_image(image_path, output_path, text, font_path="json/NotoSansJP-Regular.ttf"):
    """
    画像の左上に枠線・テキスト・凡例の色付き線を追加する
    :param image_path: 入力画像のパス
    :param output_path: 出力画像のパス
    :param text: 描画するテキスト
    :param font_path: 日本語フォントのパス
    """
    try:
        # 画像を開く
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)

        # テキスト枠の設定
        box_x, box_y = 20, 20  # 左上からの座標
        box_width, box_height = 400, 180  # 枠のサイズ
        border_color = (255, 0, 0)  # 赤色
        border_width = 4

        # 枠を描画
        draw.rectangle(
            [(box_x, box_y), (box_x + box_width, box_y + box_height)],
            outline=border_color, width=border_width, fill=(255, 255, 255)
        )

        # テキスト描画の設定
        font_size = 24
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            print("フォントが見つからないため、デフォルトフォントを使用します。")
            font = ImageFont.load_default()

        text_color = (0, 0, 0)  # 黒色
        text_position = (box_x + 10, box_y + 10)

        # テキストの描画
        draw.text(text_position, text, fill=text_color, font=font)

        # 凡例の色付き線を描画
        legend_x, legend_y = box_x + 10, box_y + 80
        legend_gap = 40

        # 大津波警報（紫色）
        draw.line([(legend_x, legend_y), (legend_x + 50, legend_y)], fill=(128, 0, 128), width=8)
        draw.text((legend_x + 60, legend_y - 10), "大津波警報", fill=text_color, font=font)

        # 津波警報（赤色）
        draw.line([(legend_x, legend_y + legend_gap), (legend_x + 50, legend_y + legend_gap)], fill=(255, 0, 0), width=8)
        draw.text((legend_x + 60, legend_y + legend_gap - 10), "津波警報", fill=text_color, font=font)

        # 津波注意報（黄色）
        draw.line([(legend_x, legend_y + 2 * legend_gap), (legend_x + 50, legend_y + 2 * legend_gap)], fill=(255, 255, 0), width=8)
        draw.text((legend_x + 60, legend_y + 2 * legend_gap - 10), "津波注意報", fill=text_color, font=font)

        # 画像を保存
        image.save(output_path)
        print(f"テキストと凡例を追加した画像が保存されました: {output_path}")

    except Exception as e:
        print("エラーが発生しました:", e)

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
