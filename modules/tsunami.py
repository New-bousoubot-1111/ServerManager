import json
import requests
import geopandas as gpd
import matplotlib.pyplot as plt
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

# フォルダ作成（必要な場合）
os.makedirs("images", exist_ok=True)

# P2P Quake APIから津波警報地域を取得
def fetch_tsunami_alerts():
    """P2P Quake APIから津波警報地域を取得"""
    url = "https://api.p2pquake.net/v2/jma/tsunami"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()  # 津波情報をJSON形式で返す
    else:
        raise ValueError(f"津波情報APIからデータを取得できませんでした。HTTPステータスコード: {response.status_code}")

# Overpass APIからGeoJSONデータを取得
def fetch_geojson_from_overpass(area_name):
    """Overpass APIからGeoJSON形式のデータを取得（エリア名を指定）"""
    url = "http://overpass-api.de/api/interpreter"
    
    # エリアIDを取得するためのクエリを作成
    query_area_id = f'[out:json]; area["name:ja"="{area_name}"]; out id;'
    
    # エリアIDを取得
    response_area = requests.get(url, params={'data': query_area_id})
    if response_area.status_code != 200:
        raise ValueError(f"エリアIDの取得に失敗しました。HTTPステータスコード: {response_area.status_code}")
    
    area_data = response_area.json()
    if not area_data.get("elements"):
        raise ValueError(f"エリア {area_name} のIDを取得できませんでした。")

    # エリアIDを取得
    area_id = area_data["elements"][0]["id"]
    print(f"エリアID: {area_id}")

    # エリアIDを使用してノード、ウェイ、リレーションを取得するクエリを作成
    query = f"""
    [out:json];
    area({area_id});  # エリアIDを使用
    (node(area); way(area); relation(area););
    out geom;
    """
    
    # エリアIDを使ってノード、ウェイ、リレーションを取得
    response = requests.get(url, params={'data': query})
    
    if response.status_code == 200:
        raw_data = response.json()
        features = []

        # ノード、ウェイ、リレーションをGeoJSONのフィーチャー形式に変換
        for element in raw_data.get("elements", []):
            if element["type"] == "node":
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [element["lon"], element["lat"]],
                    },
                    "properties": element.get("tags", {}),
                })
            elif element["type"] == "way":
                coordinates = [[nd["lon"], nd["lat"]] for nd in element.get("geometry", [])]
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString" if len(coordinates) == 2 else "Polygon",
                        "coordinates": coordinates if len(coordinates) == 2 else [coordinates],
                    },
                    "properties": element.get("tags", {}),
                })
            elif element["type"] == "relation":
                # リレーションの処理（必要に応じて拡張）
                pass

        # GeoJSON形式を構築
        geojson_data = {
            "type": "FeatureCollection",
            "features": features,
        }

        # フィーチャーが存在する場合に返す
        if len(geojson_data['features']) > 0:
            return geojson_data
        else:
            raise ValueError("GeoJSONデータに特徴が含まれていません。")
    else:
        raise ValueError(f"Overpass APIからデータを取得できませんでした。HTTPステータスコード: {response.status_code}")

# 地図を生成する関数
def generate_map(tsunami_alert_areas, geojson_data):
    """津波警報地図を生成し、ローカルパスを返す"""
    geojson_names = [feature['properties'].get('name', '') for feature in geojson_data['features']]
    gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
    gdf["color"] = "#767676"  # 全地域を灰色に設定

    for area_name, alert_type in tsunami_alert_areas.items():
        matched_region = process.extractOne(area_name, geojson_names)
        if matched_region and matched_region[1] >= 80:  # 一致度が80%以上
            gdf.loc[gdf['properties'].apply(lambda x: x.get('name', '') == matched_region[0]), "color"] = ALERT_COLORS.get(alert_type, "white")

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
    return output_path

# 津波警報情報を取得し、地図を生成して送信する
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

                tsunami_alert_areas = {
                    area["name"]: area.get("grade") for area in tsunami.get("areas", [])
                }

                # Overpass APIを使って、津波警報地域のGeoJSONデータを取得
                for area_name in tsunami_alert_areas.keys():
                    geojson_data = fetch_geojson_from_overpass(area_name)

                    # 地図を生成
                    map_path = generate_map(tsunami_alert_areas, geojson_data)
                    embed = create_embed(tsunami)
                    embed.set_image(url="attachment://tsunami.png")

                    # Discordに送信
                    with open(map_path, "rb") as file:
                        discord_file = File(file, filename="tsunami.png")
                        await tsunami_channel.send(embed=embed, file=discord_file)

                self.tsunami_sent_ids.add(tsunami_id)
                self.save_tsunami_sent_ids()

def setup(bot):
    bot.add_cog(tsunami(bot))
