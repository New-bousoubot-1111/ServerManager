import sqlite3
import nextcord
from nextcord.ext import commands, tasks
import requests
from colorama import Fore
import util
import json
import os

# 既存のキャッシュデータを読み込みまたは初期化
CACHE_FILE = 'json/cache.json'

# 保存するデータ
cache_data = {
    "result": {
        "status": "success",
        "message": "",
        "is_auth": True
    },
    "report_time": "2022/05/05 14:55:50",
    "region_code": "",
    "request_time": "20220505145550",
    "region_name": "福島県沖",
    "longitude": "141.7",
    "is_cancel": False,
    "depth": "40km",
    "calcintensity": "2",
    "is_final": True,
    "is_training": False,
    "latitude": "37.7",
    "origin_time": "20220505145501",
    "security": {
        "realm": "/kyoshin_monitor/static/jsondata/eew_est/",
        "hash": "b61e4d95a8c42e004665825c098a6de4"
    },
    "magunitude": "3.5",
    "report_num": "4",
    "request_hypo_type": "eew",
    "report_id": "20220505145510",
    "alertflg": "予報"
}

# データをキャッシュファイルに保存
with open(CACHE_FILE, 'w') as f:
    json.dump(cache_data, f, indent=4)

print("キャッシュが保存されました。")

# SQLiteデータベースファイルのパス
DB_FILE = "db/cache.db"

# SQLiteデータベースの初期化
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # `sent_reports`テーブルを作成
    c.execute('''CREATE TABLE IF NOT EXISTS sent_reports (
                    report_time TEXT PRIMARY KEY
                  )''')
    conn.commit()
    conn.close()

# 送信済み報告を取得
def get_sent_reports():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT report_time FROM sent_reports')
    reports = [row[0] for row in c.fetchall()]
    conn.close()
    return reports

# 新しい報告をDBに追加
def add_sent_report(report_time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO sent_reports (report_time) VALUES (?)', (report_time,))
    conn.commit()
    conn.close()

# DBの初期化
init_db()

# 設定ファイルの読み込み
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
        res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/{now}.json")
        if res.status_code == 200:
            data = res.json()

            # DBから送信済み報告を取得
            sent_reports = get_sent_reports()
            if data["report_time"] not in sent_reports:
                eew_channel = self.bot.get_channel(int(config["eew_channel"]))
                if data["is_training"]:
                    return
                if data["is_cancel"]:
                    embed = nextcord.Embed(
                        title="緊急地震速報がキャンセルされました",
                        description="先ほどの緊急地震速報はキャンセルされました",
                        color=0x00ffee,
                    )
                    await eew_channel.send(embed=embed)
                    return

                # 警報と予報の処理
                title = (
                    f"緊急地震速報 第{data['report_num']}報(予報)"
                    if data["alertflg"] == "予報"
                    else f"緊急地震速報 第{data['report_num']}報(警報)"
                )
                color2 = 0x00ffee if data["alertflg"] == "予報" else 0xff0000

                time = util.eew_time()
                embed = nextcord.Embed(
                    title=title,
                    description=f"{time}頃、**{data['region_name']}**で地震が発生しました。\n"
                                f"最大予想震度: **{data['calcintensity']}**\n"
                                f"深さ: **{data['depth']}**\n"
                                f"マグニチュード: **{data['magunitude']}**",
                    color=color2,
                )
                await eew_channel.send(embed=embed)

                # 送信済みリストに追加し、DBに保存
                add_sent_report(data["report_time"])

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
                embed.add_field(name="最大震度", value=round(data['maxScale'] / 10), inline=False)
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
