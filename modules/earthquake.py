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
                    data JSONB
                );
            """)
            conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
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
        try:
            # 現在時刻の取得
            now = util.eew_now()
            if now == 0:
                return

            # 最新の緊急地震速報データを取得
            res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/{now}.json")
            if res.status_code != 200:
                return

            data = res.json()
            cache = load_data_from_db()  # PostgreSQLからキャッシュを取得

            # 緊急地震速報のデータが空でない場合
            if data['result']['message'] == "":
                # キャッシュとの比較
                if cache and cache.get('report_time') == data['report_time'] and cache.get('report_num') == data['report_num']:
                    return  # 既に送信済みの速報であれば何もしない

                eew_channel = self.bot.get_channel(int(config['eew_channel']))
                image = False

                if data['is_training']:
                    return  # 訓練モードは無視

                if data['is_cancel']:
                    # キャンセル速報の場合
                    embed = nextcord.Embed(
                        title="緊急地震速報がキャンセルされました",
                        description="先ほどの緊急地震速報はキャンセルされました",
                        color=color
                    )
                    await eew_channel.send(embed=embed)
                    save_data_to_db(data)  # キャンセル情報をキャッシュに保存
                    return

                # 通常の緊急地震速報メッセージ作成
                if data['alertflg'] == "予報":
                    start_text = ""
                    title = f"緊急地震速報 第{data['report_num']}報(予報)"
                    alert_color = 0x00ffee  # ブルー
                    image = data['is_final']  # 最終報であれば画像送信
                elif data['alertflg'] == "警報":
                    start_text = "<@&1192026173924970518>\n**誤報を含む情報の可能性があります。\n今後の情報に注意してください**\n"
                    title = f"緊急地震速報 第{data['report_num']}報(警報)"
                    alert_color = 0xff0000  # レッド
                    image = True

                # 発生時刻と震源情報をフォーマット
                time = util.eew_time()
                time2 = util.eew_origin_time(data['origin_time'])
                embed = nextcord.Embed(
                    title=title,
                    description=f"{start_text}{time}{time2}頃、**{data['region_name']}**で地震が発生しました。\n"
                                f"最大予想震度は**{data['calcintensity']}**、震源の深さは**{data['depth']}Km**、"
                                f"マグニチュードは**{data['magunitude']}**と推定されます。",
                    color=alert_color
                )
                await eew_channel.send(embed=embed)

                # 必要に応じて画像を送信
                if image:
                    await util.eew_image(eew_channel)

                # データをキャッシュに保存
                save_data_to_db(data)
        except Exception as e:
            print(f"Error in eew_check: {e}")

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
