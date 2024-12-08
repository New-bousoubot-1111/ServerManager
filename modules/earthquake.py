import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from colorama import Fore
import psycopg2
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

    # 緊急地震速報
    @tasks.loop(seconds=2)
    async def eew_check(self):
        now = util.eew_now()
        if now == 0:
            logging.info("eew_now returned 0. Skipping.")
            return

        try:
            url = f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/20240104122709.json"
            logging.info(f"Fetching data from: {url}")

            res = requests.get(url)
            if res.status_code != 200:
                logging.error(f"API request failed with status code {res.status_code}")
                return

            data = res.json()
            logging.debug(f"API Response: {data}")

            if data.get('result', {}).get('message') != "":
                logging.info("No earthquake data available.")
                return

            cache = load_data_from_db()
            logging.debug(f"Cache data: {cache}")

            if cache.get('report_time') == data.get('report_time'):
                logging.info("No new data to process.")
                return

            eew_channel = self.bot.get_channel(int(config['eew_channel']))
            if not eew_channel:
                logging.error("Failed to fetch eew_channel. Check channel ID.")
                return

            # Earthquake data processing
            logging.info("Sending earthquake alert...")
            embed = nextcord.Embed(
                title="緊急地震速報",
                description="地震が発生しました。",
                color=color
            )
            await eew_channel.send(embed=embed)

            save_data_to_db(data)

        except Exception as e:
            logging.error(f"Error in eew_check: {e}")


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

def setup(bot):
    return bot.add_cog(earthquake(bot))
