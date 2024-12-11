import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from colorama import Fore
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw
import geopandas as gpd
import matplotlib.pyplot as plt
from nextcord import File

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

# 地図画像とポリゴンデータの準備
image_path = "./images/tsunami.png.shp"  # 地図画像のパス
map_data_path = "./images/tsunami.png.shp"  # Shapefileデータのパス

# 地図データを読み込む (例: GeoPandasを使用)
japan_map = gpd.read_file(map_data_path)

class tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.previous_link = None  # previous_linkを初期化

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|tsunami       |" + Fore.RESET)
        print(Fore.BLUE + "|--------------|" + Fore.RESET)
        self.check_tsunami.start()

    # 津波警報をチェックする関数
    @tasks.loop(minutes=1)
    async def check_tsunami(self):
        url = "https://api.p2pquake.net/v2/jma/tsunami"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                # 津波が発表されているエリアのリストを作成
                tsunami_alert_areas = []
                for tsunami in data:
                    if not tsunami["cancelled"]:  # 発表中の警報のみ処理
                        for area in tsunami.get("areas", []):
                            tsunami_alert_areas.append(area["name"])
                # 地図画像を読み込む
                map_image = Image.open(image_path)
                draw = ImageDraw.Draw(map_image)
                # 地図データとの対応付けと色付け
                for _, row in japan_map.iterrows():
                    prefecture_name = row["nam_ja"]
                    if prefecture_name in tsunami_alert_areas:
                        geometry = row["geometry"]
                        if geometry.type == "Polygon":
                            coords = lat_lon_to_pixel(geometry, map_image.size)
                            draw.polygon(coords, fill=(255, 0, 0, 128))  # 半透明の赤
                        elif geometry.type == "MultiPolygon":
                            for poly in geometry:
                                coords = lat_lon_to_pixel(poly, map_image.size)
                                draw.polygon(coords, fill=(255, 0, 0, 128))
                # 画像を保存
                output_path = "/mnt/data/colored_map.png"
                map_image.save(output_path)
                # Discordチャンネルに送信
                tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
                if tsunami_channel:
                    await tsunami_channel.send(
                        "津波警報が発表されている地域の地図です。",
                        file=File(output_path)
                    )

def setup(bot):
    return bot.add_cog(tsunami(bot))
