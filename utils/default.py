import time
import json
import discord
import traceback
import re
import timeago as timesince
from io import BytesIO


def config(filename: str = "config"):
    """Holt default config file"""
    try:
        with open(f"{filename}.json", encoding='utf8') as data:
            return json.load(data)
    except FileNotFoundError:
        raise FileNotFoundError("JSON file was not found")


def default_react_message():
    msg = "\
    Create a ticket to open a private channel with staff regarding help and reporting someone.\n\
    React with :envelope_with_arrow:\
    "
    return msg

def ticket_commmand_overview():
    embed = discord.Embed(title="Command overview", colour=0xd1a11b)
    embed.add_field(name="Available commands:", value=f"**{config()['prefix'][0]}close** - closes the ticket \n"
                                                      f"**{config()['prefix'][0]}invite <user_id>** - adds user to ticet\n"
                                                      f"**{config()['prefix'][0]}remove <user_id>** - removes user from ticket\n")
    return embed

def default_welcome_message():
    msg = "Staff will arrive shortly! Please send your message."
    return msg


"""Bessere Errorformattierung"""


def traceback_marker(err, advance: bool = True):
    _traceback = ''.join(traceback.format_tb(err.__traceback__))
    error = ("```py\n{1}{0}: {2}\n```").format(type(err).__name__, _traceback, err)
    return error if advance else f"{type(err).__name__}: {err}"


def timeago(target):
    return timesince.format(target)


def timetext(name):
    """ Timestamp, but in text form """
    return f"{name}_{int(time.time())}.txt"


def date(target, clock=True):
    if not clock:
        return target.strftime("%d %B %Y")
    return target.strftime("%d %B %Y, %H:%M")


def responsible(target, reason):
    responsible = f"[ {target} ]"
    if not reason:
        return f"{responsible} no reason given..."
    return f"{responsible} {reason}"


def actionmessage(case, mass=False):
    output = f"**{case}** the user"

    if mass:
        output = f"**{case}** the IDs/Users"

    return f"✅ Successfully {output}"


async def prettyResults(ctx, filename: str = "Results", resultmsg: str = "Here's the results:", loop=None):
    if not loop:
        return await ctx.send("The result was empty...")

    pretty = "\r\n".join([f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)])

    if len(loop) < 15:
        return await ctx.send(f"{resultmsg}```ini\n{pretty}```")

    data = BytesIO(pretty.encode('utf-8'))
    await ctx.send(
        content=resultmsg,
        file=discord.File(data, filename=timetext(filename.title())))


def getFileName_FromCd(cd):
    """ Get filename from content-disposition """
    if not cd:
        return None

    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None

    return fname[0]
