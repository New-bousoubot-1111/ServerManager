import json
import requests
from PIL import Image, ImageDraw
from nextcord.ext import commands, tasks
from nextcord import File
from colorama import Fore

# config ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

# 津波画像のパス
image_path = "./images/tsunami.png"  # ベースとなる地図画像
output_path = "./images/colored_map.png"

# 津波警報の種類に対応する色
ALERT_COLORS = {
    "大津波警報": (255, 0, 255, 128),  # 紫
    "津波警報": (255, 0, 0, 128),     # 赤
    "津波注意報": (255, 255, 0, 128)  # 黄
}

# 地域名と座標を定義（例として簡略化、実際には地図に対応した座標を設定）
AREA_COORDINATES = {
    "北海道": [(600, 100), (700, 200)],  # 左上と右下の座標
    "東北地方": [(650, 200), (750, 300)],
    "関東地方": [(700, 300), (800, 400)],
    "伊豆諸島": [(720, 500), (770, 550)],
    "小笠原諸島": [(750, 600), (800, 650)]
    # 他の地域の座標も追加
}

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
        url = "https://api.p2pquake.net/v2/jma/tsunami"  # 津波API
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                tsunami_alert_areas = []  # 警報発表中の地域を格納
                area_alert_types = {}    # 地域ごとの警報種類を保存

                for tsunami in data:
                    if not tsunami["cancelled"]:  # 発表中の警報のみ処理
                        for area in tsunami.get("areas", []):
                            area_name = area["name"]
                            alert_type = area.get("kind", "津波注意報")
                            tsunami_alert_areas.append(area_name)
                            area_alert_types[area_name] = alert_type

                # 地図画像に色付け
                map_image = Image.open(image_path).convert("RGBA")
                draw = ImageDraw.Draw(map_image, "RGBA")

                for area, coords in AREA_COORDINATES.items():
                    if area in tsunami_alert_areas:
                        alert_type = area_alert_types.get(area, "津波注意報")
                        color = ALERT_COLORS.get(alert_type, (255, 255, 255, 128))
                        draw.rectangle(coords, fill=color)

                # 画像を保存
                map_image.save(output_path)

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
