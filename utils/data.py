import discord
from utils import permissions, default
from discord.ext.commands import AutoShardedBot, DefaultHelpCommand

"""Autosharted Bot Version: Besser um große Bots zu handlen"""
class Bot(AutoShardedBot):
    def __init__(self, *args, prefix=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = prefix

    async def on_message(self, message):
        if not self.is_ready() or message.author.bot:
            return  # kann, bzw, muss nicht reagieren

        await self.process_commands(message)


class HelpFormat(DefaultHelpCommand):
    """
    Overrides von DefaultHelpCommand
    Hilft bei Help-Command und Debug features
    """
    def get_destination(self, no_pm: bool = False):
        if no_pm:
            return self.context.channel
        return self.context.author

    async def send_error_message(self, error):
        config = default.config()
        destination = config["dev_channel"]
        await destination.send(error)

    async def send_command_help(self, command):
        self.add_command_formatting(command)
        # paginator hilft bei formattierung
        self.paginator.close_page()
        await self.send_pages(no_pm=True)

    async def send_pages(self, no_pm: bool = False):
        try:
            if permissions.can_handle(self.context, "add_reactions"):
                await self.context.message.add_reaction(chr(0x2709))
        except discord.Forbidden:
            pass

        try:
            destination = self.get_destination(no_pm=no_pm)
            for page in self.paginator.pages:
                await destination.send(page)
        except discord.Forbidden:
            destination = self.get_destination(no_pm=True)
            await destination.send("Couldn't send help to you due to blocked DMs...")


