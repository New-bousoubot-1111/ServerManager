import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from colorama import Fore
import xml.etree.ElementTree as ET

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

class tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.previous_link = None  # previous_linkを初期化

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|tasks         |" + Fore.RESET)
        print(Fore.BLUE + "|--------------|" + Fore.RESET)
        self.news_info.start()

    # ニュース速報
    @tasks.loop(seconds=2)
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
                
                # もし前回のリンクが異なれば、ニュースを送信
                if self.previous_link != link:
                    embed = nextcord.Embed(title=title, description=link, color=color)
                    news_channel = self.bot.get_channel(int(config['news_channel']))
                    await news_channel.send(embed=embed)
                    self.previous_link = link  # 前回のリンクを更新
                else:
                    return  # 以前と同じニュースなら何もしない
            else:
                return
        else:
            return


def setup(bot):
    return bot.add_cog(tasks(bot))
