from utils import default

owners = default.config()["owners"]

def is_owner(ctx):
    return ctx.author.id in owners
