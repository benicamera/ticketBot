from discord.ext import commands
import sqlite3 as sqlite
from utils import permissions


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="exec-sql", help="Returns the result of the SQL command.")
    async def exec_sql(self, ctx, command: str):
        if not permissions.is_owner(ctx):
            await ctx.send("No permission")
            return
        db = sqlite.connect('main.db')
        cursor = db.cursor()
        try:
            cursor.execute(command)
            await ctx.send("**Successful**")
        except Exception as e:
            await ctx.send(f"Execution error: `{e}`")
        try:
            result = cursor.fetchall()
            if len(result) > 15:
                await ctx.send(f"`Result lenght: {len(result)}`")
            elif len(result) == 0:
                await ctx.send("`Empty result`")
            else:
                await ctx.send(f"`{str(result)}`")
        except Exception as e:
            await ctx.send(f"Result error: `{e}`")
        try:
            db.commit()
        except Exception as e:
            await ctx.send(f"Commit error: `{e}`")

        cursor.close()
        db.close()


def setup(bot):
    bot.add_cog(Admin(bot))
