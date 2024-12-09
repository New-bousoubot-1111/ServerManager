import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from colorama import Fore
import psycopg2
import os
from dateutil import parser
from datetime import datetime
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
    print("Database connection successful")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS earthquake_cache (
                    id SERIAL PRIMARY KEY,
                    data JSONB
                );
            """)
            conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        print(f"DATABASE_URL: {DATABASE_URL}")
    finally:
        conn.close()

# データを保存する関数
def save_data_to_db(data):
    conn = connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO earthquake_cache (data) VALUES (%s)", (json.dumps(data),))
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
            return {}
    except Exception as e:
        print(f"Error loading data from database: {e}")
        return {}
    finally:
        conn.close()

# 初期化処理
connect_db()
initialize_database()

# 設定ファイル読み込み
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

    # 緊急地震速報チェック
    @tasks.loop(seconds=2)
    async def eew_check(self):
        try:
            now = self.get_current_eew_time()
            if not now:
                return

            res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/20241209032640.json")
            if res.status_code != 200:
                return

            data = res.json()
            cache = load_data_from_db()

            if data['result']['message'] == "" and cache.get('report_time') != data['report_time']:
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

                title, start_text, alert_color, image_required = self.generate_eew_message(data)
                embed = nextcord.Embed(
                    title=title,
                    description=f"{start_text}{self.format_eew_time(data)}",
                    color=alert_color
                )
                await eew_channel.send(embed=embed)

                if image_required:
                    await self.send_eew_image(eew_channel)

                save_data_to_db(data)
        except Exception as e:
            print(f"Error in eew_check: {e}")

    # 緊急地震速報のメッセージ生成
    def generate_eew_message(self, data):
        if data['alertflg'] == "予報":
            title = f"緊急地震速報 第{data['report_num']}報(予報)" if not data['is_final'] else "緊急地震速報 最終報(予報)"
            color = 0x00ffee
            image_required = data['is_final']
        elif data['alertflg'] == "警報":
            title = f"緊急地震速報 第{data['report_num']}報(警報)" if not data['is_final'] else "緊急地震速報 最終報(警報)"
            color = 0xff0000
            image_required = True
        start_text = "<@&1192026173924970518>\n**誤報を含む情報の可能性があります。\n今後の情報に注意してください**\n" if data['alertflg'] == "警報" else ""
        return title, start_text, color, image_required

    # 緊急地震速報の発生時間フォーマット
    def format_eew_time(self, data):
        origin_time = parser.parse(data['origin_time'])
        formatted_time = origin_time.strftime("%Y年%m月%d日 %H:%M:%S")
        return f"{formatted_time}頃、**{data['region_name']}**で地震が発生しました。\n最大予想震度は**{data['calcintensity']}**、震源の深さは**{data['depth']}Km**、マグニチュードは**{data['magunitude']}**と推定されます。"

    # 地震情報チェック
    @tasks.loop(seconds=2)
    async def eew_info(self):
        try:
            request = requests.get('https://api.p2pquake.net/v2/history?codes=551&limit=1')
            if request.status_code != 200:
                return

            response = request.json()[0]
            earthquake_data = response['earthquake']
            hypocenter = earthquake_data['hypocenter']
            eew_channel = self.bot.get_channel(int(config['eew_channel']))

            embed = nextcord.Embed(
                title="地震情報",
                description=f"{self.format_earthquake_time(earthquake_data['time'])}頃、最大震度**{round(earthquake_data['maxScale'] / 10)}**の地震がありました。",
                color=self.get_intensity_color(earthquake_data['maxScale'])
            )
            embed.add_field(name="震源地", value=hypocenter['name'], inline=False)
            embed.add_field(name="マグニチュード", value=hypocenter['magnitude'], inline=False)
            embed.add_field(name="震源の深さ", value=f"{hypocenter['depth']}Km", inline=False)
            embed.set_footer(text=datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y/%m/%d %H:%M'))
            await eew_channel.send(embed=embed)
        except Exception as e:
            print(f"Error in eew_info: {e}")

    # 時間フォーマット
    def format_earthquake_time(self, time_str):
        earthquake_time = parser.parse(time_str)
        return earthquake_time.strftime('%H時%M分')

    # 震度に応じた色
    def get_intensity_color(self, max_scale):
        intensity = round(max_scale / 10)
        colors = {1: 0x6c757d, 2: 0x6c757d, 3: 0x28a745, 4: 0xffc107, 5: 0xff7f00, 6: 0xdc3545, 7: 0x6f42c1}
        return colors.get(intensity, 0x6c757d)

def setup(bot):
    bot.add_cog(earthquake(bot))
