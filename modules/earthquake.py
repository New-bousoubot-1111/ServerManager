import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from colorama import Fore
import psycopg2
import os
import util
from dateutil import parser
from datetime import datetime
import pytz

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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS earthquake_cache (
                    id SERIAL PRIMARY KEY,
                    data JSONB
                );
            """)
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

# キャッシュを削除する関数（デバッグ用）
def clear_cache():
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM earthquake_cache;")
            conn.commit()
            print("キャッシュをクリアしました。")
    finally:
        conn.close()

# データベースを初期化する関数
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

# データベース接続テスト
def test_db_connection():
    try:
        conn = connect_db()
        print("Connection successful")
        conn.close()
    except Exception as e:
        print("Error connecting to the database:", e)
        print("DATABASE_URL:", DATABASE_URL)

# テスト実行
test_db_connection()
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

    # 緊急地震速報タスク
    @tasks.loop(seconds=2)
    async def eew_check(self):
        now = util.eew_now()
        if now == 0:
            return
        res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/20241209032700.json")
        if res.status_code == 200:
            data = res.json()
            cache = load_data_from_db()  # PostgreSQLからキャッシュを取得

            print("現在のキャッシュ:", cache)
            print("APIデータ:", data)

            if not cache:
                print("キャッシュが空です。新しいデータを保存します。")
                save_data_to_db(data)
                return

            if cache.get('report_time') != data.get('report_time'):
                eew_channel = self.bot.get_channel(int(config['eew_channel']))
                if data['is_training']:
                    return
                if data['is_cancel']:
                    embed = nextcord.Embed(
                        title="緊急地震速報がキャンセルされました",
                        description="先ほどの緊急地震速報はキャンセルされました",
                        color=color
                    )
                    await eew_channel.send(embed=embed)
                    return

                alert_type = data['alertflg']
                if alert_type == "予報":
                    title = f"緊急地震速報 第{data['report_num']}報(予報)"
                    embed_color = 0x00ffee
                elif alert_type == "警報":
                    title = f"緊急地震速報 第{data['report_num']}報(警報)"
                    embed_color = 0xff0000
                else:
                    title = "緊急地震速報"
                    embed_color = color

                embed = nextcord.Embed(
                    title=title,
                    description=f"最大予想震度は**{data['calcintensity']}**、震源の深さは**{data['depth']}**、マグニチュードは**{data['magunitude']}**と推定されます。",
                    color=embed_color
                )
                await eew_channel.send(embed=embed)

                # キャッシュを更新
                save_data_to_db(data)

    # 地震情報タスク
    @tasks.loop(seconds=2)
    async def eew_info(self):
        with open('json/id.json', 'r') as f:
            id = json.load(f)['eew_id']
        data = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1').json()[0]["points"]
        if data[0]["isArea"] is False:
            isArea = "この地震による津波の心配はありません" if not data[0]["isArea"] else "この地震で津波が発生する可能性があります\n今後の情報に注意してください"
        request = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1')
        response = request.json()[0]
        data = response['earthquake']
        hypocenter = data['hypocenter']
        if request.status_code == 200:
            if id != response['id']:
                # 震度に応じた色の設定
                max_scale = round(data['maxScale'] / 10)
                if max_scale == 1:
                    color = 0x6c757d  # グレー
                    image = "images/shindo1.png"
                elif max_scale == 2:
                    color = 0x6c757d  # グレー
                    image = "images/shindo2.png"
                elif max_scale == 3:
                    color = 0x28a745  # 緑色
                    image = "images/shindo3.png"
                elif max_scale == 4:
                    color = 0xffc107  # 黄色
                    image = "images/shindo4.png"
                elif max_scale == 5:
                    color = 0xff7f00  # オレンジ色
                    image = "images/shindo5.png"
                elif max_scale == 6:
                    color = 0xdc3545  # 赤色
                    image = "images/shindo6.png"
                elif max_scale == 7:
                    color = 0x6f42c1  # 紫色
                    image = "images/shindo7.png"
                else:
                    color = 0x6c757d  # デフォルト色

                earthquake_time = parser.parse(data['time'])
                formatted_time = earthquake_time.strftime('%H時%M分')
                japan_timezone = pytz.timezone('Asia/Tokyo')
                current_time = datetime.now(japan_timezone).strftime('%Y/%m/%d %H:%M')
                embed = nextcord.Embed(title="地震情報", description=f"{formatted_time}頃、最大震度**{round(data['maxScale'] / 10)}**の地震がありました。\n{isArea}", color=color)
                embed.add_field(name="震源地", value=hypocenter['name'], inline=False)
                embed.add_field(name="マグニチュード", value=hypocenter['magnitude'], inline=False)
                embed.add_field(name="震源の深さ", value=f"{hypocenter['depth']}Km", inline=False)
                embed.set_footer(text=current_time)
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
