import os

import discord
from utils import default
from utils.data import Bot, HelpFormat

config = default.config()
print("Logging in...")

bot = Bot(
    command_prefix=config['prefix'],
    prefix=config['prefix'],
    owner_ids=config['owners'],
    command_attrs=dict(hidden=True),
    help_command=HelpFormat(),
)

for file in os.listdir("cogs"):
    if file.endswith("py"):
        name = file[:-3]
        bot.load_extension(f"cogs.{name}")

try:
    bot.run(config['token'])
except Exception as e:
    print(f"Error: {e}")

