import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from colorama import Fore
import psycopg2
import os
import util
from datetime import datetime
from dateutil import parser
import pytz

# PostgreSQL接続情報（Railwayの環境変数を使用）
DATABASE_URL = os.getenv("DATABASE_URL")  # Railwayで設定した環境変数

# データベース接続
def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

# データベース初期化
def initialize_database():
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS earthquake_cache (
                    id SERIAL PRIMARY KEY,
                    report_time TEXT NOT NULL,
                    data JSONB NOT NULL
                );
            """)
            conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        conn.close()

# データを保存する関数
def save_data_to_db(report_time, data):
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO earthquake_cache (report_time, data) VALUES (%s, %s) ON CONFLICT (report_time) DO NOTHING;",
                (report_time, json.dumps(data))
            )
            conn.commit()
    except Exception as e:
        print(f"Error saving data to database: {e}")
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
            return None
    except Exception as e:
        print(f"Error loading data from database: {e}")
        return None
    finally:
        conn.close()

# 初期化処理
initialize_database()

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

class earthquake(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            return
        res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/20241209032640.json")
        if res.status_code == 200:
            data = res.json()
            cache = load_data_from_db()  # キャッシュをPostgreSQLから取得
            if cache is None or cache.get('report_time') != data['report_time']:
                eew_channel = self.bot.get_channel(int(config['eew_channel']))
                if data['is_training'] or data['result']['message'] != "":
                    return

                if data['is_cancel']:
                    embed = nextcord.Embed(
                        title="緊急地震速報がキャンセルされました",
                        description="先ほどの緊急地震速報はキャンセルされました",
                        color=color
                    )
                    await eew_channel.send(embed=embed)
                    return

                alert_flag = data['alertflg']
                title = f"緊急地震速報 第{data['report_num']}報({alert_flag})"
                color2 = 0xff0000 if alert_flag == "警報" else 0x00ffee
                description = (
                    f"{util.eew_time()}{util.eew_origin_time(data['origin_time'])}頃、**{data['region_name']}**で地震が発生しました。\n"
                    f"最大予想震度は**{data['calcintensity']}**、震源の深さは**{data['depth']}**、マグニチュードは**{data['magunitude']}**と推定されます。"
                )
                embed = nextcord.Embed(title=title, description=description, color=color2)
                await eew_channel.send(embed=embed)

                save_data_to_db(data['report_time'], data)  # PostgreSQLにデータを保存

    # 地震情報
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
    bot.add_cog(earthquake(bot))
