import discord

from utils import default

owners = default.config()["owners"]

def is_owner(ctx):
    return ctx.author.id in owners

def can_handle(ctx, permission: str):
    """ Checks if bot has permissions or is in DMs right now """
    return isinstance(ctx.channel, discord.DMChannel) or getattr(ctx.channel.permissions_for(ctx.guild.me), permission)