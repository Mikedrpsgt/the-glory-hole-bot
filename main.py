import discord
from discord.ext import commands, tasks
import sqlite3
import os
import asyncio
import random

# Database Setup
conn = sqlite3.connect('orders.db')
c = conn.cursor()

# Create Tables
c.execute('''CREATE TABLE IF NOT EXISTS rewards 
             (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, loyalty_tier TEXT DEFAULT 'Flirty Bronze')''')

conn.commit()

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True # Added message content intent
intents.members = True # Added members intent
bot = commands.Bot(command_prefix="!", intents=intents)

# Brand Assets
MAIN_LOGO_URL = "https://yourhost.com/main-logo.png"
FOOTER_IMAGE_URL = "https://yourhost.com/footer.png"

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

# Start background tasks
@tasks.loop(hours=24)
async def daily_report():
    """Daily business report."""
    await bot.wait_until_ready()

    try:
        # Get application owner
        app_info = await bot.application_info()
        owner = app_info.owner

        if not owner:
            print("❌ Error: Could not find bot owner")
            return

        # Create report embed
        embed = discord.Embed(title="📊 Daily Business Report", color=discord.Color.blue())

        c.execute("SELECT COUNT(*) FROM rewards")
        total_users = c.fetchone()[0]

        embed.add_field(name="👥 Total Users", value=f"**{total_users}** Sweet Souls", inline=False)
        embed.set_footer(text="Sweet Holes Bake Shop - Serving Sweetness & Sass 🍩💖")

        await owner.send(embed=embed)
    except Exception as e:
        print(f"❌ Error in daily report: {str(e)}")

@bot.event
async def on_ready():
    # Start background tasks
    update_loyalty.start()
    daily_report.start()
    print(f'{bot.user} has connected to Discord!')

bot.run("YOUR_BOT_TOKEN") #Remember to replace YOUR_BOT_TOKEN with your actual bot token