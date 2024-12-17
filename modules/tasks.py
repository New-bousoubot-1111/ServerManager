import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from colorama import Fore
import xml.etree.ElementTree as ET
import asyncpg
import os

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

class tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = None

    async def setup_db(self):
        """PostgreSQLとの接続プールを作成します"""
        self.pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"))

        # 初回起動時にテーブルを作成
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS news_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

    async def get_cache(self, key):
        """キャッシュからデータを取得"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("SELECT value FROM news_cache WHERE key = $1", key)
            return result['value'] if result else None

    async def set_cache(self, key, value):
        """キャッシュにデータを保存"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO news_cache (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value
            """, key, value)

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|tasks         |" + Fore.RESET)
        print(Fore.BLUE + "________________" + Fore.RESET)
        await self.setup_db()
        self.news_info.start()

    # ニュース速報
    @tasks.loop(seconds=60)
    async def news_info(self):
        RSS_URL = "https://news.yahoo.co.jp/rss/topics/top-picks.xml"
        response = requests.get(RSS_URL)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            items = root.findall("./channel/item")
            if items:
                latest_item = items[0]
                title = latest_item.find("title").text
                link = latest_item.find("link").text

                previous_link = await self.get_cache("previous_link")

                if previous_link != link:
                    embed = nextcord.Embed(title=title, description=link, color=color)
                    news_channel = self.bot.get_channel(int(config['news_channel']))
                    await news_channel.send(embed=embed)
                    await self.set_cache("previous_link", link)
                else:
                    return
            else:
                return
        else:
            return

def setup(bot):
    return bot.add_cog(tasks(bot))
