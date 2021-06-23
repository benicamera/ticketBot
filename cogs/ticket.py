import discord
from discord.ext import commands
import sqlite3
import time
from utils import default


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # wenn eine Reaktion auf einer Nachricht eines Servers registriert wird
    # payload enthält sämtliche Daten
    # level-1
    @commands.Cog.listener()
    @commands.guild_only()
    async def on_raw_reaction_add(self, payload):
        # wenn die Reaktion von einem Bot kommt
        if payload.member.bot:
            return

        # sql-connection
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # wenn Reaktion auf welcome-message
        cursor.execute("SELECT id FROM tickets WHERE welcome_msg_id = ?", [payload.message_id])
        s = cursor.fetchone()
        if s is not None:
            cursor.close()
            db.close()
            await self._closing_react(payload)
            return

        # wenn Reaktion auf close-message
        cursor.execute("SELECT id FROM tickets WHERE close_msg_id = ?", [payload.message_id])
        s = cursor.fetchone()
        if s is not None:
            cursor.close()
            db.close()
            await self._closing_action(payload, s[0])
            return

    # wenn eine Nachricht gesendet wird
    # message enthält ein discord.Message Objekt
    # level-1
    @commands.Cog.listener()
    async def on_message(self, message):

        channel = message.channel

        # sql-verbindung
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # wenn nicht in einem Ticket-Channel
        cursor.execute("SELECT id FROM tickets WHERE channel_id = ?", [channel.id])
        r = cursor.fetchone()
        if r is None:
            cursor.close()
            db.close()
            return

        # log-message erstellen und in log speichern
        log = f"{message.author.name}#{message.author.discriminator or ''}:: Message: {message.content}\n" \
              f"Attachements: {''.join([str(a.url) + ' | ' for a in message.attachments])}\n" \
              f"Message ID: {message.id} | Message URL: {message.jump_url}"
        self._write_log(r[0], log)

    # Level-2 Funktion sendet log eines Tickets mit der Id t_id in den channel
    async def _send_log(self, channel: discord.TextChannel, t_id: int):
        await channel.send(f"Log of ticket {t_id}: ", file=discord.File(f"logs/{t_id}_log.txt"))

    # Level-3 Funktion verarbeitet Reaktionen auf eine close-message
    async def _closing_action(self, payload: discord.RawReactionActionEvent, t_id: id):

        channel = await self.bot.fetch_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)

        if payload.emoji.name == "📖":
            await self._send_log(channel, t_id)
            # Reaktionen erneuern
            await msg.clear_reaction("📖")
            await msg.clear_reaction("🔓")
            await msg.clear_reaction("🚮")
            await msg.add_reaction("📖")
            await msg.add_reaction("🔓")
            await msg.add_reaction("🚮")
            return

        if payload.emoji.name == "🔓":
            await self._reopen(channel.id, payload.user_id, self.bot.get_guild(payload.guild_id))
            # Reaktionen erneuern
            await msg.clear_reaction("🔓")
            await msg.clear_reaction("🚮")
            await msg.add_reaction("🔓")
            await msg.add_reaction("🚮")
            return

        if payload.emoji.name == "🚮":
            await self._shutdown(channel.id, payload.user_id)
            # Reaktionen erneuern
            await msg.clear_reaction("🔓")
            await msg.clear_reaction("🚮")
            await msg.add_reaction("🔓")
            await msg.add_reaction("🚮")
            return

    # Level-3 Funktion: schließt / löscht Ticket
    async def _shutdown(self, channel_id: int, user_id: int):
        print(10)
        # sql-verbindung
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # wenn channel kein Ticket-Channel
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ?", [channel_id])
        r = cursor.fetchone()
        if r is None:
            cursor.close()
            db.close()
            return

        # wenn noch offen, oder bereits gelöscht
        if r[6] == 1 or r[6] == -1:
            return
        print(10)
        user = await self.bot.fetch_user(user_id)

        # status aktualisieren, channel löschen und log machen
        cursor.execute("UPDATE tickets SET status=-1 WHERE channel_id = ?", [channel_id])
        channel = await self.bot.fetch_channel(channel_id)
        await channel.delete()
        log = f"System:: {user.name}#{user.discriminator or ''} shut down ticket-{r[0]}!"
        self._write_log(r[0], log)
        # TODO: DELETE LOGS AND DATABSES! (only needed in big distribution)

    # Level-1 Funktion: Fügt log-message zu log hinzu
    @commands.command(name="log", help="Adds the message to the ticket log.")
    @commands.guild_only()
    async def write_log(self, ctx, ticket_id: int, log_message: str):
        # sql-verbindung
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # wenn ticket nicht existiert
        cursor.execute("SELECT cat_name FROM tickets WHERE id=?", [ticket_id])
        r = cursor.fetchone()[0]
        if r is None:
            await ctx.send(f"This ticket does not exist")
            cursor.close()
            db.close()
            return

        # Rollen checken
        cursor.execute(f"SELECT role_id FROM {r}")
        s = cursor.fetchall()
        permitted = False
        # alle rollen eines Nutzers
        for role in ctx.author.roles:
            # alle Moderationsrollen der Kategorie
            for r_id in s:
                # wenn sie übereinstimmen
                if r_id[0] == role.id or role.id == default.config()["admin_role_id"]:
                    permitted = True
                    # escape for-loop
                    continue

        # wenn keine Moderationsrolle
        if not permitted:
            await ctx.send("You have no permission to do this")
            db.close()
            cursor.close()
            return

        # log
        self._write_log(ticket_id, f"LOG-COMMAND by {ctx.author}:: {log_message}")
        await ctx.message.delete()

        # close sql-connection
        cursor.close()
        db.close()

    # level-3 function schreibt log
    def _write_log(self, t_id: int, log_msg: str):
        with open(f"logs/{t_id}_log.txt", 'a') as lf:
            log = f"t: {str(time.ctime())} - {log_msg}\n\n"
            lf.write(log)

    # Level-2 Funktion: öffnet Ticket
    async def open_ticket(self, guild: discord.Guild, cat: str, user_id: int):
        # SQL- verbindung
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # erstelle ticket id
        cursor.execute("SELECT id FROM tickets ORDER BY id DESC")
        r = cursor.fetchone()
        if r is None:
            t_id = 1
        else:
            t_id = int(r[0]) + 1

        # Erstelle Channel mit Berechtigungen
        category = discord.utils.get(guild.categories, name=cat)
        member = await guild.fetch_member(user_id)
        channel = await guild.create_text_channel(f"ticket-{t_id}", category=category,
                                                  topic=f"{member.nick or member.name}'s ({member.name}#{member.discriminator}) {cat} ticket! Welcome!")
        await self.set_view_perms(self, channel, member, True)

        # hole welcome-message
        cursor.execute("SELECT welcome_msg FROM categories WHERE name=?", [cat])
        w_msg_text = cursor.fetchone()[0]

        # Zeit als String
        open_time = str(time.asctime(time.gmtime()))

        # Welcome-message mit Embed machen
        emd = discord.Embed(title=f"{member.nick or member.name}'s ({member.name}) {cat} ticket!", color=0xd1a11b)
        emd.add_field(name="Welcome!", value=w_msg_text)
        emd.set_footer(text=f"React with 🔒 to close this ticket - {open_time}")
        w_msg = await channel.send(f"{member.mention} Welcome!", embed=emd)
        await w_msg.add_reaction("🔒")
        await w_msg.pin()  # pinnt Nachricht als wichtige Nachricht an

        # Alle datenbankrelevanten Dinge machen:
        # tickets-Tabelle eintrag machen
        cursor.execute(
            f"INSERT INTO tickets (id, cat_id, cat_name, channel_id, opener_id, time, status, welcome_msg_id) VALUES ({t_id}, {category.id}, ?, {channel.id}, {user_id}, ?, 1, {w_msg.id})",
            [cat, open_time])
        # moderations-Tabelle erstellen
        cursor.execute(f"CREATE TABLE {category.name + str(t_id)} (user_id INTEGER PRIMARY KEY, highest_role TEXT)")
        # mitglieder-Tabelle erstellen
        cursor.execute(f"CREATE TABLE members{t_id} (user_id INTEGER PRIMARY KEY)")
        # Ticketöffner hinzufügen
        cursor.execute(f"INSERT INTO members{t_id} (user_id) VALUES (?)", [user_id])
        # log machen
        self._write_log(self, t_id, f"System:: {cat} ticket with ID {t_id} opened by {member.name} ({member.id})")

        # sql-änderungen vermerken und verbindungen schließen
        db.commit()
        cursor.close()
        db.close()

    # Level-3 bearbeitet Sichtbarkeitsbestimmungen eines Discordchannels für einen bestimmten Member
    async def set_view_perms(self, channel: discord.TextChannel, member: discord.Member, visible: bool):
        perms = channel.overwrites_for(member)
        perms.view_channel = visible
        await channel.set_permissions(member, overwrite=perms)

    # Level-1 Schickt die Information eines Tickets
    @commands.command(name="ticket-info", help="Sends an overview with relevant data about the ticket.")
    @commands.guild_only()
    async def t_info(self, ctx, ticket_id: int):
        # typing() lässt den Bot "schreiben". Signalisiert, dass Prozess am laufen ist
        async with ctx.channel.typing():
            # sql-verbindung
            db = sqlite3.connect('main.db')
            cursor = db.cursor()

            # wenn ticket nicht existiert
            cursor.execute(f"SELECT * FROM tickets WHERE id=?", [ticket_id])
            r = cursor.fetchone()
            if r is None:
                await ctx.send("No such ticket found.")
                db.close()
                cursor.close()
                return

            # durchsucht rollen
            cursor.execute(f"SELECT role_id FROM {r[2]}")
            s = cursor.fetchall()
            permitted = False
            for role in ctx.author.roles:
                for r_id in s:
                    if r_id[0] == role.id or role.id == default.config()["admin_role_id"]:
                        permitted = True
                        continue
            # wenn keine Erlaubnis
            if not permitted:
                await ctx.send("You have no permission to do this")
                cursor.close()
                db.close()
                return

            # suche alle Ticket-Mitglieder
            cursor.execute(f"SELECT user_id FROM members{r[0]}")
            u = cursor.fetchall()

            # suche öffner
            opener = await ctx.guild.fetch_member(r[4])
            roles = [discord.utils.get(ctx.guild.roles, id=r_id[0]) for r_id in s]

            # liste alle Mitglieder auf
            members = [await ctx.guild.fetch_member(u_id[0]) for u_id in u]
            show_roles = ', '.join(
                [f"<@&{x.id}>" for x in sorted(roles, key=lambda x: x.position, reverse=True) if
                 x.id != ctx.guild.default_role.id]
            ) if len(roles) > 1 else 'None'
            show_members = "\n".join([f"{m.mention}" for m in members])

            # erstelle Embed
            embed = discord.Embed(title=f"INFO - TICKET {r[2]} {r[0]}")
            embed.add_field(name="Opener", value=f"{opener.mention}", inline=True)
            embed.add_field(name="Opening Time", value=r[5])
            embed.add_field(name="Participants", value=show_members, inline=False)
            embed.add_field(name="Moderating Roles", value=show_roles, inline=False)

            # Fasse Status als Wörter

            status = "open"
            if r[6] == 0:
                status = "closed"
            elif r[6] == -1:
                status = "shutdown"
            # Embed Fußzeile
            embed.set_footer(text=f"Status: {status.upper()}")
            # Schicke Embed
            await ctx.send(embed=embed)

            cursor.close()
            db.close()

    # Level-1 Setzt das Thema eines Tickets
    @commands.command(name="topic", help="Sets the topic of the ticket.")
    @commands.guild_only()
    async def topic(self, ctx, topic: str):
        # sql-verbindung
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # wenn Kommando nicht in einem Ticket ausgeführt
        cursor.execute("SELECT * FROM tickets WHERE channel_id=?", [ctx.channel.id])
        r = cursor.fetchone()
        if r is None:
            await ctx.send(f"You are not in a ticket channel")
            cursor.close()
            db.close()
            return

        # Topic in Datenbank aktualisieren
        cursor.execute("UPDATE tickets SET topic=? WHERE channel_id=?", (topic, ctx.channel.id))
        cursor.close()
        db.commit()
        db.close()

        # Thema des Discordchannels ändern
        member = await ctx.guild.fetch_member(ctx.author.id)
        await ctx.channel.edit(topic=f"{member.nick or member.name}'s ({member.name}#{member.discriminator}) ticket about '{topic}'")
        await ctx.message.add_reaction("✅")

        log = f"System:: {ctx.author.name}#{ctx.author.discriminator or ''} set topic to {topic}"
        self._write_log(r[0], log)

    # Level-1 fügt Nutzer zu Ticket hinzu
    @commands.command(name="add-user", help="Let's you add a user the ticket, the command is executed in.")
    @commands.guild_only()
    async def add_user(self, ctx, userid: int):
        #   sql
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # wenn nicht in ticket channel
        cursor.execute("SELECT * FROM tickets WHERE channel_id=?", [ctx.channel.id])
        r = cursor.fetchone()
        if r is None:
            await ctx.send(f"You are not in a ticket channel")
            cursor.close()
            db.close()
            return

        # hole nutzer und Füge ihn hinzu
        added_user = await self.bot.fetch_user(userid)
        added = await self._add_user(r[0], ctx.channel, ctx.guild, added_user)
        if added:
            log = f"Add-Command by {ctx.author}:: Added {added_user} - {added_user.id}"
            self._write_log(r[0], log)
            emd = discord.Embed(color=0xd1a11b)
            emd.add_field(name="User added", value=f"{added_user.mention} has been added by {ctx.author.mention}.")
            await ctx.send(embed=emd)
        await ctx.message.add_reaction("✅")
        cursor.close()
        db.close()

    # level 2: Fügt user hinzu
    async def _add_user(self, t_id: int, channel: discord.TextChannel, guild: discord.Guild, user: discord.User):
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # wenn schon hinzugefügt
        cursor.execute(f"SELECT * FROM members{t_id} WHERE user_id=?", [user.id])
        r = cursor.fetchone()
        if r is not None:
            await channel.send("User already added")
            return False
        # lasse User das Ticket sehen
        m = await guild.fetch_member(user.id)
        await self.set_view_perms(channel, m, True)
        #Füge User der Datenbank hinzu
        cursor.execute(f"INSERT INTO members{t_id} (user_id) VALUES (?)", [user.id])
        db.commit()
        cursor.close()
        db.close()
        return True

    # level-1 Entfernt Benuter, der Hinzugefügt wurde
    @commands.command(name="remove-user", help="Let's you remove a user the ticket, the command is executed in.")
    @commands.guild_only()
    async def remove_user(self, ctx, *, userid: int):
        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id=?", [ctx.channel.id])
        r = cursor.fetchone()
        if r is None:
            await ctx.send(f"You are not in a ticket channel")
            cursor.close()
            db.close()
            return
        # entferne Benutzer
        added_user = await self.bot.fetch_user(userid)
        removed = await self._remove_user(r[0], ctx.channel, ctx.guild, added_user)
        if removed:
            log = f"Remove-Command by {ctx.author}:: Removed {added_user} - {added_user.id}"
            self._write_log(r[0], log)
            emd = discord.Embed(color=0xd1a11b)
            emd.add_field(name="User removed", value=f"{added_user.mention} has been removed by {ctx.author.mention}.")
            await ctx.send(embed=emd)
        await ctx.message.add_reaction("✅")
        cursor.close()
        db.close()

    # level-2 Entfernt Benutzer
    async def _remove_user(self, t_id: int, channel: discord.TextChannel, guild: discord.Guild, user: discord.User):
        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        cursor.execute(f"SELECT cat_name FROM tickets WHERE id=?", [t_id])
        s = cursor.fetchone()[0]

        # kontrolliere, ob benutzer Moderator ist
        member = await guild.fetch_member(user.id)
        cursor.execute(f"SELECT * FROM {s}")
        roles = cursor.fetchall()
        for role in member.roles:
            for r_id in roles:
                if r_id[0] == role.id:
                    await channel.send("Can't remove the user due to their roles.")
                    return False

        # ist Benutzer im Ticket?
        cursor.execute(f"SELECT * FROM members{t_id} WHERE user_id=?", [user.id])
        r = cursor.fetchone()
        if r is None:
            await channel.send("User not found")
            return False
        await self.set_view_perms(channel, member, False)
        cursor.execute(f"DELETE FROM members{t_id} WHERE user_id=?", [user.id])
        db.commit()
        cursor.close()
        db.close()
        return True

    # level-1 Schliesse Ticket
    @commands.command(help="Closes the ticket, the command is executed in.")
    @commands.guild_only()
    async def close(self, ctx):
        if not self.is_in_ticket(ctx.channel.id):
            await ctx.send("❌ Execute this command in a ticket channel!")
            return
        await self._close(ctx.channel.id, ctx.author.id, ctx.guild)

    # level-2 schließe Ticket
    async def _close(self, channel_id: int, user_id: int, guild: discord.Guild):
        # sql
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # ist in Ticket
        cursor.execute("SELECT id, cat_name, status FROM tickets WHERE channel_id = ?", [channel_id])
        r = cursor.fetchone()
        if r is None:
            cursor.close()
            db.close()
            return

        # ist geschlossen oder gelöscht
        if r[2] == 0 or r[2] == -1:
            return

        user = await self.bot.fetch_user(user_id)

        # moderationsrollen sollen weiterhin chat lesen können
        cursor.execute(f"SELECT * FROM {r[1]}")
        roles = cursor.fetchall()
        channel = await self.bot.fetch_channel(channel_id)
        async with channel.typing():
            cursor.execute(f"SELECT user_id FROM members{r[0]}")
            member_ids = cursor.fetchall()
            members = [await guild.fetch_member(m_id[0]) for m_id in member_ids]
            for m in members:
                immune = False
                for role in m.roles:
                    for r_id in roles:
                        if r_id[0] == role.id:
                            immune = True
                            continue
                if immune:
                    continue

                # nicht moderationsrollen werden entfernt
                await self.set_view_perms(channel, m, False)

            # channel wird umbenannt
            new_name = f"closed-{r[0]}"
            cursor.execute(f"SELECT closed_cat_id FROM categories WHERE name=?", [r[1]])
            s = cursor.fetchone()
            closed_category = guild.get_channel(s[0])
            await channel.send("Ticket is closing, this might take a while...")
            try:
                await channel.edit(category=closed_category)
            except Exception as e:
                print(e)
            await channel.edit(name=new_name)
            # log
            log = f"System:: {user.name}#{user.discriminator or ''} closed ticket-{r[0]}!"
            self._write_log(r[0], log)

            # closed-message
            emd = discord.Embed(color=0xC22E00)
            mbr = await guild.fetch_member(user.id)
            emd.add_field(name=f"Ticket closed", value=f"This ticket has been closed by {mbr.mention}")
            emd.add_field(name="Actions:", value="📖 get logs\n"
                                                 "🔓 reopen ticket\n"
                                                 "🚮 delete ticket", inline=False)
            msg = await channel.send(embed=emd)
            await msg.add_reaction("📖")
            await msg.add_reaction("🔓")
            await msg.add_reaction("🚮")
            await msg.pin()

            cursor.execute("UPDATE tickets SET status=0 WHERE channel_id = ?", [channel_id])
            cursor.execute(f"UPDATE tickets SET close_msg_id={msg.id} WHERE id={r[0]}")

        db.commit()
        cursor.close()
        db.close()

    # level-2 verarbeitet Reaktionen, die Ticket schliessen
    async def _closing_react(self, payload: discord.RawReactionActionEvent):
        # finde channel und nachricht der Reaktion
        channel = await self.bot.fetch_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)

        # wenn aktzeptiert
        if payload.emoji.name == "✅":
            for r in msg.reactions:
                # wenn nachgefragt -> schliessen
                if r.emoji == "❌":
                    await self._close(payload.channel_id, payload.user_id, self.bot.get_guild(payload.guild_id))
                    await msg.clear_reaction("✅")
                    await msg.clear_reaction("❌")
                    return
            await msg.clear_reaction("✅")
            return

        # wenn abgelehnt
        if payload.emoji.name == "❌":
            # entferne alle Reaktionen
            try:
                await msg.clear_reaction("✅")
                await msg.clear_reaction("❌")
            except:
                pass
            return

        # wenn wille zum schliessen, frage nach
        if payload.emoji.name == "🔒":
            await msg.clear_reaction("🔒")
            await msg.add_reaction("🔒")
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            return
        await msg.clear_reaction(payload.emoji.name)

    # level-1 öffne geschlossenes ticket
    @commands.command(name="reopen", help="Reopens the ticket, the command is executed in.")
    @commands.guild_only()
    async def reopen(self, ctx):
        print(1)
        if not self.is_in_ticket(ctx.channel.id):
            await ctx.send(f"You are not in a ticket channel")
            return
        await self._reopen(ctx.channel.id, ctx.author.id, ctx.guild)
        await ctx.message.add_reaction("✅")

    # level-2 öffnet geschlossenes ticket
    async def _reopen(self, channel_id: int, user_id: int, guild: discord.Guild):
        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        print(2)
        cursor.execute("SELECT * FROM tickets WHERE channel_id = ?", [channel_id])
        r = cursor.fetchone()
        if r is None:
            cursor.close()
            db.close()
            return
        # wenn offen oder gelöscht
        if r[6] == 1 or r[6] == -1:
            return

        user = await self.bot.fetch_user(user_id)

        channel = await self.bot.fetch_channel(channel_id)
        cursor.execute(f"SELECT user_id FROM members{r[0]}")
        member_ids = cursor.fetchall()
        members = [await guild.fetch_member(m_id[0]) for m_id in member_ids]

        # wieder alle Mitglieder hinzufügen
        for m in members:
            await self.set_view_perms(channel, m, True)

        print(3)
        cursor.execute(f"SELECT cat_id FROM categories WHERE name=?", [r[2]])
        open_category = closed_category = guild.get_channel(cursor.fetchone()[0])
        # ticket umbennenen
        await channel.edit(name=f"ticket-{r[0]}", category=open_category)
        log = f"System:: {user.name}#{user.discriminator or ''} re-opened ticket-{r[0]}!"
        self._write_log(r[0], log)
        emd = discord.Embed(color=0x79ee09)
        mbr = await guild.fetch_member(user.id)
        emd.add_field(name=f"Ticket re-opened",
                      value=f"This ticket has been re-opened by {mbr.mention}. Please wait a few minutes before closing again!")
        await channel.send(embed=emd)

        cursor.execute("UPDATE tickets SET status=1 WHERE channel_id = ?", [channel_id])
        db.commit()
        cursor.close()
        db.close()

    # Hilfsfunktion. Schaut ob channel.id == Ticket.
    # Kommt nicht oft zum einsatz, da man anderweitg mit einer SQL-Abfrage mehr Daten bekommen kann.
    def is_in_ticket(self, c_id: int):
        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tickets WHERE channel_id=?", [c_id])
        r = cursor.fetchone()
        cursor.close()
        db.close()
        if r is None:
            return False
        return True

    # level-1: Wird ausgeführt, wenn Nachricht bearbeitet wird
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        db = sqlite3.connect('main.db')
        cursor = db.cursor()

        # wenn Nachricht in Ticket
        cursor.execute("SELECT id FROM tickets WHERE channel_id = ?", [channel.id])
        r = cursor.fetchone()
        if r is None:
            cursor.close()
            db.close()
            return

        # suche alte Nachricht
        cached_message = payload.cached_message
        if cached_message is None:
            old_attachments_url = []
            old_message = "Old message not found"
        else:
            # wenn gefunden: Liste alle Anhang-URLs
            old_attachments_url = [str(a.url) + ' | ' for a in cached_message.attachments]
            old_message = cached_message.content

        # schreibe Log
        new_message = await channel.fetch_message(payload.message_id)
        log = f"System - Message of {new_message.author} edited:: Old Message: {old_message}\n" \
              f"Old Attachements: {''.join(old_attachments_url)}\n" \
              f"-------------------------\n" \
              f"New Message: {new_message.content}\n" \
              f"New Attachements: {''.join([str(a.url) + ' | ' for a in new_message.attachments])}\n" \
              f"Message ID: {new_message.id} | Message URL: {new_message.jump_url}"

        with open(f"logs/{r[0]}_log.txt", 'a') as lf:
            _log = f"t: {str(time.ctime())} - {log}\n\n"
            lf.write(_log)


def setup(bot):
    bot.add_cog(Ticket(bot))
