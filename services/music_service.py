import asyncio
from random import shuffle

import disnake.ui
from disnake import AudioSource, Embed, Color, FFmpegPCMAudio, \
    VoiceChannel, TextChannel, User, ApplicationCommandInteraction
from disnake.ext.commands import Bot
from disnake.ui import Button
from yt_dlp import YoutubeDL, DownloadError

from _types import DSServer, MusicInfo
from config import FFMPEG_OPTIONS, YDL_OPTIONS
from exceptions import ServerNotFoundException, VoiceChatException


class MusicService:
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

        self.__servers: dict[int, DSServer] = {}

    def get_server(self, guild_id: int) -> DSServer | None:
        return self.__servers.get(guild_id, None)

    async def play(
            self,
            inter: ApplicationCommandInteraction,
            query: str,
            next: bool = False,
    ) -> str:
        if not inter.author.voice:
            raise VoiceChatException(f'{inter.author.mention}, connect to a voice channel')

        server = self.__add_server(inter.guild.id)

        connected_to_voice_channel = await self.__connect_to_voice_channel(
            server,
            inter.author.voice.channel
        )

        if not connected_to_voice_channel:
            raise VoiceChatException('Couldn\'t connect to the voice channel')

        await inter.response.defer()
        music = self.__ydl_search(query)

        if music is None:
            return 'Music not found. Try a different url'

        self.__add_music_to_queue(server, music, next)

        if not server.voice_client.is_playing():
            await self.__play_music(server, inter.channel)

        return f'{inter.author.mention} | Added `{music.title}` by `{music.author}` in queue'

    def __add_server(self, guild_id: int) -> DSServer:
        if not self.get_server(guild_id):
            self.__servers[guild_id] = DSServer(id=guild_id)
        return self.__servers[guild_id]

    def __add_music_to_queue(
            self,
            server: DSServer,
            music: MusicInfo,
            next: bool = False,
    ) -> None:
        if next:
            server.music_queue.insert(0, music)
        else:
            server.music_queue.append(music)

    async def __play_music(self, server: DSServer, text_channel: TextChannel) -> None:
        if server.player_message:
            await server.player_message.delete()
            server.player_message = None

        if server.music_queue:
            music = server.music_queue.pop(0)

            audio_src: AudioSource = FFmpegPCMAudio(
                source=music.url,
                executable='ffmpeg/ffmpeg.exe',
                **FFMPEG_OPTIONS,
            )

            embed, buttons = await self.__create_player(music)
            server.player_message = await text_channel.send(embed=embed, components=buttons)

            server.voice_client.play(
                audio_src,
                after=lambda e: asyncio.run_coroutine_threadsafe(self.__play_music(server, text_channel), self.bot.loop)
            )

    @staticmethod
    async def __create_player(music: MusicInfo) -> tuple[Embed, list[Button]]:
        embed = Embed(
            title='Now playing', description=f'`{music.title}` by `{music.author}`',
            color=Color.purple()
        )
        buttons = [
            Button(label="Pause", style=disnake.ButtonStyle.blurple,
                   emoji=disnake.PartialEmoji(name='pause', id=1059394116439515136), custom_id='pause'),
            Button(label="Stop", style=disnake.ButtonStyle.red,
                   emoji=disnake.PartialEmoji(name='stop', id=1053672684820631612), custom_id='stop'),
            Button(label="Skip", style=disnake.ButtonStyle.green,
                   emoji=disnake.PartialEmoji(name='skip', id=1053664978298740776), custom_id='skip'),
            Button(label="Shuffle", style=disnake.ButtonStyle.green,
                   emoji=disnake.PartialEmoji(name='shuffle', id=1065366332108976238), custom_id='shuffle'),
            Button(label="Queue", style=disnake.ButtonStyle.grey,
                   emoji='📃', custom_id='queue'),
        ]
        return embed, buttons

    async def __connect_to_voice_channel(self, server: DSServer, voice_channel: VoiceChannel) -> bool:
        # if not server.voice_client or not server.voice_client.is_connected():
        if not self.is_connected(server.id):
            server.voice_client = await voice_channel.connect()

            if not server.voice_client:
                return False
        elif server.voice_client.channel != voice_channel:
            await server.voice_client.move_to(voice_channel)
        return True

    @staticmethod
    def __ydl_search(query: str) -> MusicInfo | None:
        with YoutubeDL(YDL_OPTIONS) as ydl:
            if query.startswith('https://'):
                try:
                    info = ydl.extract_info(query, download=False)
                except DownloadError:
                    info = None
            else:
                info = ydl.extract_info(f'ytsearch:{query}', download=False)['entries'][0]

        if info:
            return MusicInfo(title=info['title'], author=info['channel'], url=info['url'])
        else:
            return

    # TODO: make addition to my music as vk (use MongoDB - {<guild_id>: list[<music_name>/MusicInfo])

    def pause(self, guild_id: int) -> str:
        server = self.get_server(guild_id)

        if not server:
            raise ServerNotFoundException(f'Server {guild_id} not found')

        if not server.voice_client.is_paused():
            server.voice_client.pause()
            return 'Current music has been paused'
        else:
            server.voice_client.resume()
            return 'Current music has been resumed'

    async def stop(self, guild_id: int) -> str:
        server = self.get_server(guild_id)

        if server:
            await self.disconnect(guild_id)
            return 'Bot has been disconnected'
        else:
            return 'Bot already disconnected'

    async def skip(self, guild_id: int) -> str:
        server = self.get_server(guild_id)

        if server and server.voice_client.is_playing():
            server.voice_client.stop()

            if server.music_queue:
                return 'Current music has been skipped'
            else:
                await self.disconnect(guild_id)
                return 'Current music has been skipped. Queue is empty'

    def get_queue(self, guild_id: int) -> str:
        server = self.get_server(guild_id)

        if server and server.music_queue:
            queue = [str(music) for music in server.music_queue]
            message = '\n'.join(queue)
            return f'Music queue:\n{message}'
        else:
            return 'Queue is empty'

    def shuffle_queue(self, guild_id: int) -> str:
        server = self.get_server(guild_id)

        if server:
            shuffle(server.music_queue)
            return f'The music queue has been shuffled'

    async def disconnect(self, guild_id: int, force: bool = False) -> None:
        server = self.get_server(guild_id)

        if server and server.voice_client:
            server.music_queue = []
            await server.voice_client.disconnect(force=force)
            if server.player_message:
                await server.player_message.delete()
                server.player_message = None
            self.__servers.pop(guild_id)
            del server

    def is_connected(self, guild_id: int) -> bool:
        server = self.get_server(guild_id)
        return server and server.voice_client and server.voice_client.is_connected()
