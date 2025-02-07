import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import sqlite3
import os
import asyncio
import random

# Database Setup
conn = sqlite3.connect('orders.db')
c = conn.cursor()

# Create Tables
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item TEXT, quantity INTEGER, status TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS rewards 
             (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, loyalty_tier TEXT DEFAULT 'Flirty Bronze')''')

c.execute('''CREATE TABLE IF NOT EXISTS feedback 
             (feedback_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, rating INTEGER, comment TEXT)''')

conn.commit()

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Brand Assets
MAIN_LOGO_URL = "https://raw.githubusercontent.com/your-repo/assets/main/logo.png"  # Update this URL
FOOTER_IMAGE_URL = MAIN_LOGO_URL  # Using same logo for footer

# Loyalty Tiers & Perks
LOYALTY_TIERS = {
    "Flirty Bronze": 0,
    "Sweet Silver": 50,
    "Seductive Gold": 100
}

# Fun Responses
PICKUP_LINES = [
    "Are you a donut? Because I’m totally glazed over you. 😉",
    "If sweetness was a crime, you’d be doing life, sugar. 😘",
    "Are you on the menu? Because I’d order you every time. 😏"
]

TRUTH_QUESTIONS = [
    "What's the sweetest thing someone has done for you? 🍯",
    "What’s your biggest guilty pleasure? (Besides me, obviously.) 😉"
]

DARE_TASKS = [
    "Send a 💋 emoji to the last person who ordered a donut. 😘",
    "Change your name to 'Sugar Daddy/Mommy' for 10 minutes. 🔥"
]

# --- Order System ---
class OrderView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Place Order", style=discord.ButtonStyle.green)
    async def place_order(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await interaction.followup.send("🍩 **Tell me what you're craving, sugar!**\n`item_name, quantity` format, baby. 😉", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        msg = await bot.wait_for("message", check=check)
        try:
            item, quantity = msg.content.split(", ")
            quantity = int(quantity)
            if quantity <= 0 or quantity > 100:
                await interaction.followup.send("⚠️ Honey, please order between 1 and 100 items! 😘", ephemeral=True)
                return
            user_id = interaction.user.id
            c.execute("INSERT INTO orders (user_id, item, quantity, status) VALUES (?, ?, ?, 'Pending')", (user_id, item, quantity))
            conn.commit()
            order_id = c.lastrowid

            embed = discord.Embed(
                title="✅ Order Placed, Sweetheart!",
                description=f"**Order ID:** `{order_id}`\n🍩 **Item:** {item}\n📦 **Quantity:** {quantity}",
                color=discord.Color.pink()
            )
            embed.set_thumbnail(url=MAIN_LOGO_URL)
            embed.set_footer(text="Sweet Holes Bake Shop - Always a treat 😉", icon_url=FOOTER_IMAGE_URL)

            message = await interaction.followup.send(embed=embed)
            await message.add_reaction("💋")

        except:
            await interaction.followup.send("⚠️ Oops, honey! Try `item_name, quantity` format. Don’t make me beg. 😘", ephemeral=True)

# --- Loyalty System ---
@tasks.loop(hours=24)
async def update_loyalty():
    """Upgrades users based on points."""
    c.execute("SELECT user_id, points FROM rewards")
    users = c.fetchall()

    for user_id, points in users:
        new_tier = "Flirty Bronze"
        for tier, min_points in LOYALTY_TIERS.items():
            if points >= min_points:
                new_tier = tier

        c.execute("UPDATE rewards SET loyalty_tier = ? WHERE user_id = ?", (new_tier, user_id))

    conn.commit()

@bot.command()
async def my_tier(ctx):
    """Check your loyalty tier."""
    user_id = ctx.author.id
    c.execute("SELECT loyalty_tier, points FROM rewards WHERE user_id = ?", (user_id,))
    result = c.fetchone()

    if result:
        tier, points = result
    else:
        tier, points = "Flirty Bronze", 0

    embed = discord.Embed(
        title="💖 Your VIP Sweet Holes Card 💖",
        description=f"👤 **{ctx.author.display_name}**\n🏅 **Loyalty Tier:** {tier}\n🎁 **Total Points:** {points}",
        color=discord.Color.pink()
    )
    embed.set_thumbnail(url=MAIN_LOGO_URL)
    embed.set_footer(text="Stay sweet, sugar! More rewards coming your way! 😘", icon_url=FOOTER_IMAGE_URL)

    await ctx.send(embed=embed)

# --- Fun Features ---
@bot.command()
async def pickup(ctx):
    """Sends a fun, flirty pick-up line."""
    line = random.choice(PICKUP_LINES)
    await ctx.send(f"💋 **Sweet Holes Flirty Line:** {line}")

@bot.command()
async def truth(ctx):
    """Gives a flirty truth question."""
    question = random.choice(TRUTH_QUESTIONS)
    await ctx.send(f"💖 **Truth:** {question}")

@bot.command()
async def dare(ctx):
    """Gives a fun dare task."""
    dare = random.choice(DARE_TASKS)
    await ctx.send(f"🔥 **Dare:** {dare}")

@bot.command()
async def daily(ctx):
    """Gives a daily bonus of points."""
    user_id = ctx.author.id
    bonus_points = random.randint(5, 15)

    c.execute("INSERT INTO rewards (user_id, points) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET points = points + ?", 
              (user_id, bonus_points, bonus_points))
    conn.commit()

    await ctx.send(f"🎉 **Daily Reward Claimed!** You earned **+{bonus_points} points!** Keep coming back for more treats! 🍩")

# --- Auto Register Commands ---
@bot.event
async def on_ready():
    """Auto syncs commands on startup."""
    await bot.tree.sync()
    update_loyalty.start()
    print("🔥 Sweet Holes VIP & Flirty Fun Bot is LIVE! 😏")

# Run the bot
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)
