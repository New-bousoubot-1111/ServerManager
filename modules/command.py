import nextcord
from nextcord.ext import commands
import requests
import json
from colorama import Fore
import util
import re
import url
import deepl

with open('json/config.json', 'r') as f:
    config = json.load(f)
with open('json/help.json', 'r') as f:
    help = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

def is_japanese(str):
    return True if re.search(r'[ぁ-んァ-ン]', str) else False

class command(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.Cog.listener()
  async def on_ready(self):
    print(Fore.BLUE + "|command       |" + Fore.RESET)

#普通
  #ping
  @nextcord.slash_command(description="応答速度を表示します")
  async def ping(self,ctx):
    embed=nextcord.Embed(title="ping", description=f"BOTのpingは**{round(self.bot.latency *1000)}**です。",color=color)
    await ctx.send(embed=embed)
      
  @nextcord.slash_command(description="botの情報やコマンドを表示します")
  async def help(self,ctx):
    creators = []
    for creator in help['owners']:
      creators.append(await self.bot.fetch_user(int(creator)))
    creators = "".join(f"\n`{x}`" for x in creators)
    commands_list = "".join(f"`{help['prefix']}{x}` " for x in help['commands_list'])
    embed=nextcord.Embed(title="情報",color=color)
    embed.add_field(name=f"作成者",value=f"{creators}")
    embed.add_field(name=f"言語",value="Python")

    embed2=nextcord.Embed(title="コマンド",description=f"***{commands_list}***",color=color)
    await ctx.send(embed=embed,view=util.help_page(embed,embed2))
    
#メッセージ展開
  @nextcord.slash_command(description="メッセージを展開できる")
  async def message_open(self,ctx,message_url=nextcord.SlashOption(name="メッセージリンク",description="展開したいメッセージのメッセージリンク")):
    await url.message_open(ctx,message_url,ctx.guild,ctx.channel,self.bot)

  @nextcord.slash_command(description="翻訳できる")
  async def translate(self,ctx, *, message=nextcord.SlashOption(name="message",description="メッセージ/messageを書いて下さい")):
    if is_japanese(message):
        lang = "EN-US"
    else:
        lang = "JA"
    
    translator = deepl.Translator("bb3b8bbd-7bc3-9431-17db-407ec264b66c:fx")
    result = translator.translate_text(message, target_lang=lang)
    result_txt = result.text

    embed = nextcord.Embed(description=result_txt, color=nextcord.Colour.from_rgb(130, 219, 216))

    await ctx.send(embed=embed)

def setup(bot):
    return bot.add_cog(command(bot))
