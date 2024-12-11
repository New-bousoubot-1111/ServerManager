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

ALERT_COLORS = {
    "大津波警報": "purple",
    "津波警報": "red",
    "津波注意報": "yellow"
}

GEOJSON_PATH = "./images/japan.geojson"
gdf = gpd.read_file(GEOJSON_PATH)

class tsunami(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|tasks         |" + Fore.RESET)
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
                            print(f"Processing area: {area['name']}")  # デバッグ用
                            alert_type = area.get("kind", "津波注意報")
                            tsunami_alert_areas[area["name"]] = alert_type

                fig, ax = plt.subplots(figsize=(10, 12))
                gdf["color"] = "white"

                unmatched_areas = []
                for index, row in gdf.iterrows():
                    matched = False
                    for area_name, alert_type in tsunami_alert_areas.items():
                        if area_name in row["NAM"]:
                            gdf.at[index, "color"] = ALERT_COLORS.get(alert_type, "white")
                            matched = True
                    if not matched:
                        unmatched_areas.append(row["NAM"])

                if unmatched_areas:
                    print(f"Unmatched areas: {unmatched_areas}")

                gdf.plot(ax=ax, color=gdf["color"], edgecolor="black")
                plt.title("津波情報", fontsize=16)

                output_path = "./images/colored_map.png"
                plt.savefig(output_path)
                print(f"Image saved at {output_path}")
                plt.show()

                tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
                if tsunami_channel:
                    await tsunami_channel.send(
                        "津波警報が発表されている地域の地図です。",
                        file=File(output_path)
                    )
                else:
                    print("Channel not found or bot lacks permissions.")
            else:
                print("No tsunami alert data available.")
        else:
            print(f"Failed to fetch tsunami data: {response.status_code}")

def setup(bot):
    bot.add_cog(tsunami(bot))
