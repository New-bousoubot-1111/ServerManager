import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from PIL import Image, ImageDraw
from nextcord import File
from colorama import Fore

# configファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

# 地図画像のパス
image_path = "./images/tsunami.png"
output_path = "./images/colored_map.png"

# 地域名と画像内座標（仮の例: 座標を手動で設定）
AREA_COORDINATES = {
    "伊豆諸島": [(100, 200), (150, 250)],  # 四角形の左上と右下
    "小笠原諸島": [(300, 400), (350, 450)]
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
        url = "https://api.p2pquake.net/v2/jma/tsunami"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                # 津波警報が発表されているエリアを取得
                tsunami_alert_areas = []
                for tsunami in data:
                    if not tsunami["cancelled"]:  # 発表中の警報のみ処理
                        for area in tsunami.get("areas", []):
                            tsunami_alert_areas.append(area["name"])

                # 地図画像に色付け
                map_image = Image.open(image_path).convert("RGBA")
                draw = ImageDraw.Draw(map_image, "RGBA")

                for area, coords in AREA_COORDINATES.items():
                    if area in tsunami_alert_areas:
                        draw.rectangle(coords, fill=(255, 0, 0, 128))  # 半透明の赤

                # 画像を保存
                map_image.save(output_path)

                # Discordチャンネルに送信
                tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
                if tsunami_channel:
                    await tsunami_channel.send(
                        "津波警報が発表されている地域の地図です。",
                        file=File(output_path)
                    )
        else:
            print("津波データの取得に失敗しました。")

def setup(bot):
    bot.add_cog(tsunami(bot))
