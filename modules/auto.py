import nextcord
from nextcord.ext import commands
import json
from colorama import Fore

with open('json/config.json','r') as f:
	config = json.load(f)

color = nextcord.Colour(int(config['color'],16))

class auto(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.Cog.listener()
  async def on_ready(self):
    print(Fore.BLUE + "|auto          |" + Fore.RESET)

  @commands.Cog.listener()
  async def on_member_join(self,member):
    channel = self.bot.get_channel(int(config['welcome_channel']))    
    embed=nextcord.Embed(title="**Welcome**",description=f"{member.name}がサーバーに参加しました",color=color)
    embed.set_author(name=member,icon_url=member.display_avatar)
    await channel.send(embed=embed)

  @commands.Cog.listener()
  async def on_member_remove(self,member):
    channel = self.bot.get_channel(int(config['welcome_channel']))    
    embed=nextcord.Embed(title="**Good bye**",description=f"{member.name}がサーバーから退室しました",color=color)
    embed.set_author(name=member,icon_url=member.display_avatar)
    await channel.send(embed=embed)

def setup(bot):
  return bot.add_cog(auto(bot))