import nextcord
import json
import asyncio
import re
import traceback

with open('json/config.json','r') as f:
	config = json.load(f)

color = nextcord.Colour(int(config['color'],16))

class message_jump(nextcord.ui.View):
  def __init__(self,jump_url):
    super().__init__(timeout=None)
    self.value = None
    self.add_item(nextcord.ui.Button(label="元のメッセージ",url=jump_url))

async def message_open(ctx,url,guild,channel,bot):
  for m in re.compile(r'https://(ptb\.|canary\.)?discord(app)?.com/channels/'r'(?P<server>[\d]{19})/(?P<channel>[\d]{19})/(?P<msg>[\d]{19})').finditer(url):
    if guild.id == int(m.group('server')):
      channel = bot.get_channel(int(m.group('channel')))
      if not channel:
        continue
      orgmsg = await channel.fetch_message(int(m.group('msg')))
      if not orgmsg:
        continue
      embed, files, embeds, jump_url = await message_open_embed(channel,orgmsg)
      await ctx.send(embed=embed,files=files,view=message_jump(jump_url))
      for embed in embeds:
        await ctx.channel.send(embed=embed)
        await asyncio.sleep(1)
      return
  else:
    embed=nextcord.Embed(title="エラー",description="URLはメッセージリンクをペーストして下さい",color=color)
    await ctx.send(embed=embed,ephemeral=True)

async def message_open_embed(channel,message):
  embed=nextcord.Embed(description=message.content,color=color)
  embed.add_field(name="メッセージの送信時間",value=f"<t:{int(message.created_at.timestamp())}:F>",inline=False)
  embed.add_field(name="チャンネル",value=f"{message.channel.name}",inline=False)  
  embed.set_author(name=message.author.display_name,icon_url=message.author.display_avatar)
  files = []
  if message.attachments:
    flag = True
    text = ''
    exts = [
      '.png','.jpg', '.jpeg', '.jpe', '.jfif', '.exif','.bmp', '.dib', '.rle','.gif'
			]
    for attachment in message.attachments:
      if (any([attachment.filename.lower().endswith(ext) for ext in exts]) and not attachment.is_spoiler() and flag):
        embed.set_image(url=attachment.url)
        flag = False
      else:
        if not attachment.is_spoiler():
          text += f"[{attachment.filename}]({attachment.url} '{attachment.filename}')\n"
        else:
          text += f"||[{attachment.filename}]({attachment.url} '{attachment.filename}')||\n"
    if text:
      embed.add_field(name="その他の添付ファイル",value=text)
  return embed, files, message.embeds, message.jump_url