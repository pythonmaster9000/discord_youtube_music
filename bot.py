from __future__ import unicode_literals
import discord
from discord.ext import commands
from collections import deque
import yt_dlp
import pytube
import re
import asyncio

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', case_insensitive=True, intents=intents)
SAVE_PATH = r''


def clean_url(url):
    if re.search("^(http(s)?:\/\/)?((w){3}.)?youtu(be|.be)?(\.com)?\/.+", url[0]):
        if 'list' in url[0]:
            return 'https://www.youtube.com/watch?v=Lst5TLrc2t8'
        return url[0]
    return f'https://www.youtube.com/watch?v={str(pytube.Search(url).results[0]).split("=")[-1]}'


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


class VcClient:
    def __init__(
            self,
            vc: discord.VoiceClient
    ):
        self.vc = vc
        self.queue = deque()

    def skip(self):
        if self.vc.is_playing():
            self.vc.stop()


class MusicCore:
    def __init__(self):
        self.vc_clients = {}
        self.waiting_period = 360

    async def play_queue(
            self,
            guild_id: str
    ):
        music_client = self.vc_clients.get(guild_id)
        while music_client and music_client.queue:
            url = music_client.queue.popleft()
            ydl_opts = {'format': 'mp4',
                        'nooverwrites': False,
                        'outtmpl': rf'{SAVE_PATH}{guild_id}.mp3'}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(url)
                print('downloaded')
            music_client.vc.play(
                discord.FFmpegPCMAudio(
                    source=rf'{SAVE_PATH}{guild_id}.mp3'))
            while music_client.vc.is_playing() and music_client.vc.is_connected():
                await asyncio.sleep(.5)
            if not music_client.vc.is_connected():
                break
        grace_period = self.waiting_period
        while grace_period != 0 and music_client.vc.is_connected():
            await asyncio.sleep(1)
            if music_client.queue:
                await self.play_queue(guild_id)
                grace_period = self.waiting_period
            grace_period -= 1
        await music_client.vc.disconnect()
        del self.vc_clients[guild_id]


core = MusicCore()


@client.command()
async def mursic(ctx, *url):
    url = clean_url(url)
    await ctx.send(url)
    if core.vc_clients.get(str(ctx.message.guild.id)) and core.vc_clients.get(str(ctx.message.guild.id)).vc.is_connected():
        core.vc_clients.get(str(ctx.message.guild.id)).queue.append(url)
        return
    vc = await ctx.message.author.voice.channel.connect()
    new_client = VcClient(vc)
    new_client.queue.append(url)
    core.vc_clients[str(ctx.message.guild.id)] = new_client
    await core.play_queue(str(ctx.message.guild.id))


@client.command()
async def skip(ctx):
    if core.vc_clients.get(str(ctx.message.guild.id)):
        core.vc_clients.get(str(ctx.message.guild.id)).skip()


client.run('')
