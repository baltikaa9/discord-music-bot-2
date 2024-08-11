import random

from disnake import ApplicationCommandInteraction, MessageInteraction, Member, VoiceState
from disnake.ext import commands
from loguru import logger

from config import BOT_DS_ID
from exceptions import ServerNotFoundException, VoiceChatException
from services import MusicService


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

        self.music_service: MusicService = MusicService(bot)
        # self.servers: dict[int, DSServer] = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        # if member.guild.id not in self.music_services:
        #     self.music_services[member.guild.id] = MusicService(self.bot)

        if (
                self.music_service.is_connected(member.guild.id) and
                before.channel and
                before.channel.id == self.music_service.get_server(member.guild.id).voice_client.channel.id and
                len(before.channel.members) == 1
        ):
            """If all members have been leaved from voice chat"""
            await self.music_service.disconnect(member.guild.id)

        if member.id == BOT_DS_ID and before.channel and not after.channel:
            """If bot has been kicked from voice chat"""
            await self.music_service.disconnect(member.guild.id, True)

    @commands.Cog.listener()
    async def on_button_click(self, inter: MessageInteraction):
        match inter.component.custom_id:
            case 'pause':
                await self.pause(inter)
            case 'stop':
                await self.stop(inter)
            case 'skip':
                await self.skip(inter)
            case 'shuffle':
                await self.shuffle_queue(inter)
            case 'queue':
                await self.get_queue(inter)
            case _:
                return

    @commands.slash_command(description='Add a song from URL or search to queue')
    async def play(
            self,
            inter: ApplicationCommandInteraction,
            query: str = commands.Param(description='The query to search')
    ):
        logger.info(
            f'Command \'/play\' | Server {inter.guild.id} - {inter.author.display_name} ({inter.author})'
        )
        try:
            message = await self.music_service.play(inter, query)
            await inter.edit_original_message(message)
        except VoiceChatException as e:
            await inter.send(str(e), ephemeral=True)

    @commands.slash_command(description='Add a song from URL or search to the top of queue')
    async def playnext(
            self,
            inter: ApplicationCommandInteraction,
            query: str = commands.Param(description='The query to search')
    ):
        logger.info(
            f'Command \'/playnext\' | Server {inter.guild.id} - {inter.author.display_name} ({inter.author})'
        )
        try:
            message = await self.music_service.play(inter, query, True)
            await inter.edit_original_message(message)
        except VoiceChatException as e:
            await inter.send(str(e), ephemeral=True)

    @commands.slash_command(description='Pause/resume the currently playing song')
    async def pause(self, inter: ApplicationCommandInteraction):
        logger.info(
            f'Command \'/pause\' | Server {inter.guild.id} - {inter.author.display_name} ({inter.author})'
        )
        try:
            message = self.music_service.pause(inter.guild.id)
            await inter.send(message)
        except ServerNotFoundException as e:
            await inter.send(
                content="There's no music currently playing, add some music with the `/play` command",
                ephemeral=True
            )

    @commands.slash_command(description='Stop the currently playing song')
    async def stop(self, inter: ApplicationCommandInteraction | MessageInteraction):
        logger.info(
            f'Command \'/stop\' | Server {inter.guild.id} - {inter.author.display_name} ({inter.author})'
        )
        message = await self.music_service.stop(inter.guild.id)
        await inter.send(message, ephemeral=True)

    @commands.slash_command(description='Skip the currently playing song')
    async def skip(self, inter: ApplicationCommandInteraction | MessageInteraction):
        logger.info(
            f'Command \'/skip\' | Server {inter.guild.id} - {inter.author.display_name} ({inter.author})'
        )
        try:
            message = await self.music_service.skip(inter.guild.id)
            await inter.send(message)
        except ServerNotFoundException as e:
            await inter.send(
                content="There's no music currently playing, add some music with the `/play` command",
                ephemeral=True
            )

    @commands.slash_command(name='queue', description='Show a music queue')
    async def get_queue(self, inter: ApplicationCommandInteraction):
        logger.info(
            f'Command \'/queue\' | Server {inter.guild.id} - {inter.author.display_name} ({inter.author})'
        )
        message = self.music_service.get_queue(inter.guild.id)
        await inter.send(message)

    @commands.slash_command(name='shuffle', description='Shuffle the music queue')
    async def shuffle_queue(self, inter: ApplicationCommandInteraction | MessageInteraction):
        logger.info(
            f'Command \'/shuffle\' | Server {inter.guild.id} - {inter.author.display_name} ({inter.author})'
        )
        message = self.music_service.shuffle_queue(inter.guild.id)
        await inter.send(message)

    @commands.slash_command()
    async def ping(self, inter: ApplicationCommandInteraction):
        # server = self.servers.get(inter.guild.id)
        print(type(inter))
        await inter.send(f'{inter.guild.id=}')
        await inter.response.send_message('Pong!')

        # if server.voice_client:
        #     await inter.send(f'connected: {server.voice_client.is_connected()}')


def setup(bot: commands.Bot):
    bot.add_cog(MusicCog(bot))
