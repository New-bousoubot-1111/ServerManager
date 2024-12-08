import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from colorama import Fore
import psycopg2
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import os
import util

# PostgreSQL接続情報（Railwayの環境変数を使用）
DATABASE_URL = os.getenv("DATABASE_URL")  # Railwayで設定した環境変数

# データベース接続
def connect_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

# データを保存する関数
def save_data_to_db(data):
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            # 必要なテーブルがまだ作成されていない場合、作成
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS earthquake_cache (
                    id SERIAL PRIMARY KEY,
                    data JSONB
                );
            """)
            # データをJSONとして挿入
            cursor.execute("INSERT INTO earthquake_cache (data) VALUES (%s)", (json.dumps(data),))
            conn.commit()
    finally:
        conn.close()

# データを読み込む関数
def load_data_from_db():
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT data FROM earthquake_cache ORDER BY id DESC LIMIT 1;")
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return {}  # データがない場合は空の辞書を返す
    finally:
        conn.close()

def test_db_connection():
    try:
        conn = connect_db()
        print("Connection successful")
        conn.close()
    except Exception as e:
        print("Error connecting to the database:", e)
        print("DATABASE_URL:", DATABASE_URL)

# コードの実行時に確認してみてください
test_db_connection()

def initialize_database():
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS earthquake_cache (
                    id SERIAL PRIMARY KEY,
                    data JSONB
                );
            """)
            conn.commit()
    finally:
        conn.close()

# Bot起動時にデータベースを初期化
initialize_database()

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

class earthquake(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.id = None

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|earthquake    |" + Fore.RESET)
        self.eew_check.start()
        self.eew_info.start()
        self.tsunami_info.start()

    # 緊急地震速報
    @tasks.loop(seconds=2)
    async def eew_check(self):
        now = util.eew_now()
        if now == 0:
            return
        res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/{now}.json")
        if res.status_code == 200:
            data = res.json()
            cache = load_data_from_db()  # PostgreSQLからキャッシュを取得
            if data['result']['message'] == "":
                if cache.get('report_time') != data['report_time']:
                    eew_channel = self.bot.get_channel(int(config['eew_channel']))
                    image = False
                    if data['is_training'] == True:
                        return
                    if data['is_cancel'] == True:
                        embed = nextcord.Embed(
                            title="緊急地震速報がキャンセルされました",
                            description="先ほどの緊急地震速報はキャンセルされました",
                            color=color
                        )
                        await eew_channel.send(embed=embed)
                        return
                    if data['alertflg'] == "予報":
                        start_text = ""
                        if data['is_final'] == False:
                            title = f"緊急地震速報 第{data['report_num']}報(予報)"
                            color2 = 0x00ffee  # ブルー
                        else:
                            title = f"緊急地震速報 最終報(予報)"
                            color2 = 0x00ffee  # ブルー
                            image = True
                    if data['alertflg'] == "警報":
                        start_text = "<@&1192026173924970518>\n**誤報を含む情報の可能性があります。\n今後の情報に注意してください**\n"
                        if data['is_final'] == False:
                            title = f"緊急地震速報 第{data['report_num']}報(警報)"
                            color2 = 0xff0000  # レッド
                        else:
                            title = f"緊急地震速報 最終報(警報)"
                            color2 = 0xff0000  # レッド
                            image = True

                    time = util.eew_time()
                    time2 = util.eew_origin_time(data['origin_time'])
                    embed = nextcord.Embed(
                        title=title,
                        description=f"{start_text}{time}{time2}頃、**{data['region_name']}**で地震が発生しました。\n最大予想震度は**{data['calcintensity']}**、震源の深さは**{data['depth']}**、マグニチュードは**{data['magunitude']}**と推定されます。",
                        color=color2
                    )
                    await eew_channel.send(embed=embed)
                    if data['report_num'] == "1":
                        image = True
                    if image == True:
                        await util.eew_image(eew_channel)

                # PostgreSQLにキャッシュを保存
                save_data_to_db(data)


    # 地震情報
    @tasks.loop(seconds=2)
    async def eew_info(self):
        with open('json/id.json', 'r') as f:
            id = json.load(f)['eew_id']
        data = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1').json()[0]["points"]
        if data[0]["isArea"] is False:
            isArea = "この地震による津波の心配はありません" if not data[0]["isArea"] else "この地震で津波が発生する可能性があります"
        request = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1')
        response = request.json()[0]
        data = response['earthquake']
        hypocenter = data['hypocenter']
        if request.status_code == 200:
            if id != response['id']:
                embed = nextcord.Embed(title="地震情報", color=color)
                embed.add_field(name="発生時刻", value=data['time'], inline=False)
                embed.add_field(name="震源地", value=hypocenter['name'], inline=False)
                embed.add_field(name="最大震度", value=round(data['maxScale']/10), inline=False)
                embed.add_field(name="マグニチュード", value=hypocenter['magnitude'], inline=False)
                embed.add_field(name="震源の深さ", value=f"{hypocenter['depth']}Km", inline=False)
                embed.add_field(name="", value=isArea, inline=False)
                embed.set_footer(text=data['time'])
                eew_channel = self.bot.get_channel(int(config['eew_channel']))
                await eew_channel.send(embed=embed)
                with open('json/id.json', 'r') as f:
                    id = json.load(f)
                    id['eew_id'] = response['id']
                with open('json/id.json', 'w') as f:
                    json.dump(id, f, indent=2)
            else:
                return

  #津波情報
  @tasks.loop(seconds=5)  # 定期的に津波情報を確認
  async def tsunami_info(self):
    # 津波情報を取得
    response = requests.get("https://api.p2pquake.net/v2/history?codes=552&limit=1")
    if response.status_code != 200:
      print("津波情報の取得に失敗しました。")
      return

    tsunami_data = response.json()[0]
    tsunami_regions = []  # 津波警報が発令されている地域の緯度・経度
    for area in tsunami_data["areas"]:
      # 仮の緯度・経度を設定（本番ではエリアごとに緯度・経度を定義）
      tsunami_regions.append((35.0, 135.0))  # サンプル値

    # 地図画像を生成
    map_file_path = self.generate_tsunami_map(tsunami_regions)

    # Discord Embed作成
    embed = nextcord.Embed(title="津波情報", color=0xFF0000)
    embed.add_field(name="発表時刻", value=tsunami_data["time"], inline=False)
    embed.add_field(name="発令地域", value=", ".join([area['name'] for area in tsunami_data["areas"]]), inline=False)
    embed.set_image(url="attachment://tsunami_map.png")  # 地図画像を設定

    # チャンネルを取得し、送信
    tsunami_channel = self.bot.get_channel(int(config['eew_channel']))
    if tsunami_channel:
      await tsunami_channel.send(embed=embed, file=nextcord.File(map_file_path))

  def generate_tsunami_map(self, tsunami_regions, output_file="tsunami_map.png"):
    """
    津波情報を地図にプロットし、画像を生成する関数。
    
    Args:
      tsunami_regions (list of tuples): 津波警報が発令されている地域の緯度と経度のリスト [(lat, lon), ...]
      output_file (str): 生成される地図画像のファイルパス
    """
    # 地図の作成
    fig = plt.figure(figsize=(12, 8))
    m = Basemap(projection='merc', llcrnrlat=20, urcrnrlat=50, llcrnrlon=120, urcrnrlon=150, resolution='i')
    m.drawcoastlines()
    m.drawcountries()
    m.drawstates()

    # 津波警報地域をプロット
    for lat, lon in tsunami_regions:
      x, y = m(lon, lat)
      m.plot(x, y, 'ro', markersize=10)  # 赤い点でプロット

    # タイトルを設定して画像を保存
    plt.title("津波情報")
    plt.savefig(output_file)
    plt.close()

    return output_file

def setup(bot):
    return bot.add_cog(earthquake(bot))
