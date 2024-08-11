from disnake import Game, Intents
from disnake.ext import commands

from cogs import MusicCog
from config import TOKEN

bot = commands.Bot(
    command_prefix='/',
    activity=Game(name='попе пальчиком'),
    help_command=None,
    intents=Intents.all(),
    reload=True,
    test_guilds=[1193283727548231720],
)


@bot.event
async def on_ready():
    print(f'bot {bot.user} is ready')


if __name__ == '__main__':
    bot.load_extensions('cogs')
    # bot.add_cog(MusicCog(bot))
    bot.run(TOKEN)
    # main()
