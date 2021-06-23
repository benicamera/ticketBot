import discord
from discord.ext import commands
import sqlite3
import time
from cogs.ticket import Ticket


class Handle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Hilfsfunktion: bearbeitet Sichtbarkeitsberechtigungen eines Nutzers in einem Kanal
    async def set_view_perms(self, channel: discord.TextChannel, member: discord.Member, visible: bool):
        perms = channel.overwrites_for(member)
        perms.view_channel = visible
        await channel.set_permissions(member, overwrite=perms)

    # Level-1 Schickt die Ticket-Historie eines Nutzers
    @commands.command(name="history", help="Sends the ticket history of an user")
    @commands.has_role("Admin")
    @commands.guild_only()
    async def get_history(self, ctx, userid: int, amount: int = None):
        # wenn keine Menge angegeben, mache 5
        amount = amount or 5

        #sql
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        cursor.execute(f"SELECT id, cat_name, time, status, topic FROM tickets WHERE opener_id=? ORDER BY id DESC",
                       [userid])
        r = cursor.fetchall()
        c = 1
        member = await ctx.guild.fetch_member(userid)
        # wenn Nutzer nicht bekannt
        if member is None:
            await ctx.send(f"{ctx.author.mention} User not found in Database.")
            return

        # Erstelle Nachricht
        embed = discord.Embed(title=f"Ticket history of {member.display_name}")
        embed.set_thumbnail(url=member.avatar_url)
        # kleine Übersicht jedes Tickets
        for res in r:
            if c > amount:
                break
            status = "open"
            if res[3] == 0:
                status = "closed"
            elif res[3] == -1:
                status = "shutdown"
            embed.add_field(name=f"{c}. ticket-{res[0]}", value=f"**Category:** {res[1]}\n  **Time:** {res[2]}\n"
                                                                f"**Topic:** {res[4]}\n  **Status:** {status}\n")
            c += 1
        # schicke Nachricht
        await ctx.send(f"{ctx.author.mention}", embed=embed)

    # level-3, Schhreibt log
    def write_log(self, t_id: int, log_msg: str):
        with open(f"logs/{t_id}_log.txt", 'a') as lf:
            log = f"t: {str(time.ctime())} - {log_msg}\n\n"
            lf.write(log)

    # level 3 schicke Log in channel
    async def _send_log(self, channel: discord.TextChannel, t_id: int):
        await channel.send(f"Log of ticket {t_id}: ", file=discord.File(f"logs/{t_id}_log.txt"))


    # level 1 sended den Log eines Tickets
    @commands.command(name="get-log", help="Sends the text file of the log from the ticket given.")
    @commands.has_role("Admin")
    @commands.guild_only()
    async def get_log(self, ctx, ticket_id: int):
        try:
            # versuche Log zu schicken
            await self._send_log(ctx.channel, ticket_id)
        except Exception as e:
            await ctx.send(f"Error occured. Probably no log existent: {e}")

    # level 1 wird ausgeführt, wenn eine Reaktion hinzugefügt wurde
    @commands.Cog.listener()
    @commands.guild_only()
    async def on_raw_reaction_add(self, payload):
        # wenn Reaktion von Bot
        if payload.member.bot:
            return
        # sql-verbindung
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # wenn opening-message
        cursor.execute("SELECT name FROM categories WHERE msg_id = ?", [payload.message_id])
        t = cursor.fetchone()
        # wenn opening-emoji
        if t is not None and payload.emoji.name == "📩":
            cursor.close()
            db.close()
            # hole Serverobjekt
            guild = self.bot.get_guild(payload.guild_id)
            # öffne Ticket
            await Ticket.open_ticket(Ticket, guild, t[0], payload.member.id)
            msg_channel = discord.utils.get(guild.channels, id=payload.channel_id)
            msg = await msg_channel.fetch_message(payload.message_id)
            # Reaktionen erneuern
            await msg.clear_reaction("📩")
            await msg.add_reaction("📩")
            return


def setup(bot):
    bot.add_cog(Handle(bot))
