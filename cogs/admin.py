from discord.ext import commands
import sqlite3 as sqlite
from utils import permissions


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # level-1 Führt sql-Anfrage aus
    @commands.command(name="exec-sql", help="Returns the result of the SQL command.")
    async def exec_sql(self, ctx, command: str):
        # wenn Bot-Eigentümer
        if not permissions.is_owner(ctx):
            await ctx.send("No permission")
            return
        # sql-verbindung
        db = sqlite.connect('main.db')
        cursor = db.cursor()
        try:
            # führe aus und sende Feedback
            cursor.execute(command)
            await ctx.send("**Successful**")
        except Exception as e:
            # sende error, wenn fehlgeschlagen
            await ctx.send(f"Execution error: `{e}`")
        try:
            # versuche das Ergebnis zu bekommen
            result = cursor.fetchall()
            # wenn ergebnis sehr groß
            if len(result) > 15:
                await ctx.send(f"`Result lenght: {len(result)}`")
            # wenn ergebnis leer
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

        # schließe Verbindung
        cursor.close()
        db.close()


def setup(bot):
    bot.add_cog(Admin(bot))
