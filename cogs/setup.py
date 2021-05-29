import discord
from discord.ext import commands
import sqlite3
from utils import default


class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(name="new-cat",
                      help="Creates new Discord category and posts react-to-open message"
                           "in the channel you give.")
    @commands.has_role("Admin")
    async def new_cat(self, ctx, channel_id: int, name: str):
        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        cursor.execute("SELECT * FROM categories WHERE name=?", [name])
        r = cursor.fetchone()
        if r is not None:
            await ctx.send("Category already exists.")
            return

        category = await ctx.guild.create_category(name)
        closed = await ctx.guild.create_category(f"{name} Closed")

        if len(name.split(" ")) > 1 or any(chr.isdigit() for chr in name):
            await ctx.send("Name invalid: No spaces and/or numbers allowed!")
            return

        await category.set_permissions(ctx.guild.default_role, view_channel=False)
        ch = await self.bot.fetch_channel(channel_id)

        eb = discord.Embed()
        eb.add_field(name=f"{name} Ticket", value=default.default_react_message())
        msg = await ch.send(embed=eb)
        await msg.add_reaction("📩")

        cursor.execute(
            f"INSERT INTO categories (name, cat_id, msg_channel, msg_id, welcome_msg, react_message, closed_cat_id) "
            f"VALUES (?, {category.id}, ?, {msg.id}, ?, ?, {closed.id})",
            [name, channel_id, default.default_welcome_message(), default.default_react_message()])
        cursor.execute(f"CREATE TABLE {name} (role_id INTEGER UNIQUE)")
        cursor.execute(f"INSERT INTO {name} (role_id) VALUES ({default.config()['admin_role_id']})")
        db.commit()
        cursor.close()
        db.close()
        await ctx.message.add_reaction("✅")

    @commands.guild_only()
    @commands.command(name="del-cat",
                      help="Deletes the Discord category and react-to-open message"
                           "of the name you give."
                      )
    @commands.has_role("Admin")
    async def del_cat(self, ctx, name: str):
        def check(message: discord.Message):
            return message.channel == ctx.channel and message.author == ctx.author

        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        cursor.execute("SELECT * FROM categories WHERE name=?", [name])
        r = cursor.fetchone()
        if r is None:
            await ctx.send("Category does not exist")
            return
        emd = discord.Embed(title=f"Delete {name} Category", colour=0xF7F9A6)
        emd.add_field(name="WARNING",
                      value=f"You are about to delete a ticket category ({name}).\n This results in deleting all tickets under this category.")
        emd.add_field(name=f"ARE YOU SURE TO DELETE {name}?", value="Y/N?")
        await ctx.send(embed=emd)
        answer = await self.bot.wait_for("message", check=check)
        if not (answer.content.lower() == "y" or answer.content.lower() == "yes"):
            await ctx.send("Deleting canceled.")
            return

        msg_channel = discord.utils.get(ctx.guild.channels, id=r[2])
        try:
            msg = await msg_channel.fetch_message(r[3])
            await msg.delete()
        except:
            pass
        cursor.execute(f"DROP TABLE IF EXISTS {name}")
        cat = discord.utils.get(ctx.guild.channels, id=r[1])
        for ch in cat.channels:
            await ch.delete()
        await cat.delete()
        cursor.execute("DELETE FROM categories WHERE name=?", [name])
        cursor.close()
        db.commit()
        db.close()
        await ctx.message.add_reaction("✅")  #

    @commands.group(name="edit-cat", help="Type 't.help edit-cat [msg|add-role|remove-role|react-msg]' (select one) for more.")
    @commands.guild_only()
    @commands.has_role("Admin")
    async def edit_cat(self, ctx):
        if ctx.invoked_subcommand is None:
            ctx.send("Subcommand needed for `edit-cat`.")

    @edit_cat.command(name="msg", help="Changes the welcome message of a category ticket.")
    @commands.guild_only()
    @commands.has_role("Admin")
    async def msg(self, ctx, category: str, text: str):
        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        cursor.execute("SELECT * FROM categories WHERE name=?", [category])
        r = cursor.fetchone()
        if r is None:
            await ctx.send("Category does not exist")
            return
        cursor.execute("UPDATE categories SET welcome_msg = ? WHERE name = ?", [text, category])
        db.commit()
        cursor.close()
        db.close()
        await ctx.message.add_reaction("✅")

    @edit_cat.command(name="add-role", help="Adds the role as moderating role. Only for new tickets.")
    @commands.guild_only()
    @commands.has_role("Admin")
    async def add_role(self, ctx, category: str, role_id: int):
        role = discord.utils.get(ctx.guild.roles, id=role_id)
        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        cursor.execute("SELECT * FROM categories WHERE name=?", [category])
        r = cursor.fetchone()
        if r is None:
            await ctx.send("Category does not exist")
            return
        cursor.execute(f"SELECT * FROM {category} WHERE role_id=?", [role_id])
        s = cursor.fetchone()
        if s is not None:
            await ctx.send("Role already added.")
            return
        cursor.execute(f"INSERT INTO {category} (role_id) VALUES (?)", [role_id])
        cursor.execute("SELECT cat_id FROM categories WHERE name=?", [category])
        category = discord.utils.get(ctx.guild.channels, id=r[1])
        await category.set_permissions(role, view_channel=True)
        db.commit()
        cursor.close()
        db.close()
        await ctx.message.add_reaction("✅")

    @edit_cat.command(name="remove-role", help="Removes the role from moderating roles. Only for new tickets.")
    @commands.guild_only()
    @commands.has_role("Admin")
    async def remove_role(self, ctx, category: str, role_id: int):
        role = discord.utils.get(ctx.guild.roles, id=role_id)
        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        cursor.execute("SELECT * FROM categories WHERE name=?", [category])
        r = cursor.fetchone()
        if r is None:
            await ctx.send("Category does not exist")
            return
        cursor.execute(f"SELECT * FROM {category}")
        s = cursor.fetchall()
        if len(r) < 2:
            await ctx.send("Can't remove more roles. Suggestion: Delete category.")
            return
        cursor.execute(f"SELECT * FROM {category} WHERE role_id=?", [role_id])
        s = cursor.fetchone()
        if s is None:
            await ctx.send("No such role found")
            return
        cursor.execute(f"DELETE FROM {category} WHERE role_id=?", [role_id])
        cursor.execute("SELECT cat_id FROM categories WHERE name=?", [category])
        category = discord.utils.get(ctx.guild.channels, id=r[1])
        await category.set_permissions(role, view_channel=False)
        db.commit()
        cursor.close()
        db.close()
        await ctx.message.add_reaction("✅")

    @edit_cat.command(name="react-msg", help="Edits the opener message of the category.")
    @commands.guild_only()
    @commands.has_role("Admin")
    async def react_msg(self, ctx, category: str, text: str):
        db = sqlite3.connect('main.db')
        cursor = db.cursor()
        cursor.execute("SELECT * FROM categories WHERE name=?", [category])
        r = cursor.fetchone()
        if r is None:
            await ctx.send("Category does not exist")
            return
        cursor.execute("UPDATE categories SET react_message = ? WHERE name = ?", [text, category])
        cursor.execute("SElECT msg_channel, msg_id FROM categories WHERE name=?", [category])
        r = cursor.fetchone()
        try:
            msg_channel = discord.utils.get(ctx.guild.channels, id=r[0])
            msg = await msg_channel.fetch_message(r[1])
            eb = discord.Embed()
            eb.add_field(name=f"{category} Ticket", value=f"{text} \n React with :envelope_with_arrow:")
            await msg.edit(embed=eb)
        except:
            await ctx.send("Error found editing the message")

        db.commit()
        cursor.close()
        db.close()
        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Setup(bot))
