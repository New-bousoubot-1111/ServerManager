import json
import requests
from colorama import Fore
import geopandas as gpd
import matplotlib.pyplot as plt
from fuzzywuzzy import process
from nextcord.ext import commands, tasks
from nextcord import File, Embed
from datetime import datetime
from dateutil import parser

# 設定ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

ALERT_COLORS = {"Advisory": "purple", "Warning": "red", "Watch": "yellow"}
GEOJSON_PATH = "./images/japan.geojson"
COASTLINE_PATH = "./images/kaigansen.json"
GEOJSON_REGION_FIELD = 'nam_ja'

# GeoJSONデータの読み込み
gdf = gpd.read_file(GEOJSON_PATH)
coastline_gdf = gpd.read_file(COASTLINE_PATH)

REGION_MAPPING = {
    "沖縄本島地方": "Okinawa Ken",
    "宮古島・八重山地方": "Okinawa Ken",
    "小笠原諸島": "東京都",
    "伊豆諸島": "東京都"
}

def generate_map(tsunami_alert_areas):
    """津波警報地図を生成し、ローカルパスを返す"""
    geojson_names = gdf[GEOJSON_REGION_FIELD].tolist()
    gdf["color"] = "#767676"  # 全地域を灰色に設定
    
    coastline_gdf = coastline_gdf.to_crs(gdf.crs)
    
    for area_name, alert_type in tsunami_alert_areas.items():
        print(f"処理中の地域: {area_name}, 警報タイプ: {alert_type}")  # デバッグログ
        matched_region = match_region(area_name, geojson_names)
        print(f"一致した地域: {matched_region}")  # デバッグログ
        
        if matched_region:
            region_gdf = gdf[gdf[GEOJSON_REGION_FIELD] == matched_region]
            if not region_gdf.empty:
                try:
                    coastal_region = gpd.overlay(region_gdf, coastline_gdf, how="intersection")
                    if not coastal_region.empty:
                        gdf.loc[gdf[GEOJSON_REGION_FIELD] == matched_region, "color"] = ALERT_COLORS.get(alert_type, "white")
                except Exception as e:
                    print(f"Error during overlay operation: {e}")
                    continue
        else:
            print(f"{area_name} は一致しませんでした。")  # 地名が一致しない場合のログ

    # 地図を描画
    try:
        fig, ax = plt.subplots(figsize=(15, 18))
        fig.patch.set_facecolor('#2a2a2a')
        ax.set_facecolor("#2a2a2a")
        ax.set_xlim([122, 153])  # 東経122度～153度（日本全体をカバー）
        ax.set_ylim([20, 46])    # 北緯20度～46度（南西諸島から北海道まで）
        gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)
        ax.set_axis_off()

        output_path = "images/tsunami.png"
        plt.savefig(output_path, bbox_inches="tight", transparent=False, dpi=300)
        plt.close()
        print("地図画像が正常に生成されました。")  # ログ
        return output_path
    except Exception as e:
        print(f"地図画像の生成中にエラーが発生しました: {e}")
        return None

def match_region(area_name, geojson_names):
    """地域名をGeoJSONデータと一致させる"""
    # 直接一致を試みる
    if area_name in geojson_names:
        return area_name
    # マッピングの利用
    if area_name in REGION_MAPPING:
        return REGION_MAPPING[area_name]
    # Fuzzyマッチング
    best_match, score = process.extractOne(area_name, geojson_names)
    print(f"Fuzzyマッチング結果: {best_match} (スコア: {score})")  # デバッグログ
    return best_match if score >= 80 else None

def create_embed(data):
    alert_levels = {
        "Advisory": {"title": "大津波警報", "color": 0x800080},
        "Warning": {"title": "津波警報", "color": 0xff0000},
        "Watch": {"title": "津波注意報", "color": 0xffff00}
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

    if not data.get("areas"):
        embed.add_field(
            name=f"{formatted_time}頃に津波警報、注意報等が解除されました。",
            value="念のため、今後の情報に気をつけてください。",
            inline=False
        )
    return embed

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

                # 地図画像の生成ログ
                print(f"警報地域: {tsunami_alert_areas}")

                if tsunami_alert_areas:
                    map_path = generate_map(tsunami_alert_areas)
                    if map_path:
                        embed.set_image(url="attachment://tsunami.png")
                        with open(map_path, "rb") as file:
                            discord_file = File(file, filename="tsunami.png")
                            await tsunami_channel.send(embed=embed, file=discord_file)
                    else:
                        print("地図画像が生成されませんでした。")
                        await tsunami_channel.send(embed=embed)
                else:
                    await tsunami_channel.send(embed=embed)

                self.tsunami_sent_ids.add(tsunami_id)
                self.save_tsunami_sent_ids()

def setup(bot):
    bot.add_cog(tsunami(bot))
