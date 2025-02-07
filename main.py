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

# Basic Commands
@bot.command(name='points')
async def check_points(ctx):
    """Check your current points and tier."""
    c.execute("SELECT points, loyalty_tier FROM rewards WHERE user_id = ?", (ctx.author.id,))
    result = c.fetchone()
    
    if not result:
        c.execute("INSERT INTO rewards (user_id) VALUES (?)", (ctx.author.id,))
        conn.commit()
        points, tier = 0, "Flirty Bronze"
    else:
        points, tier = result

    embed = discord.Embed(title="🏆 Your Loyalty Status", color=discord.Color.gold())
    embed.add_field(name="Points", value=str(points), inline=True)
    embed.add_field(name="Tier", value=tier, inline=True)
    await ctx.send(embed=embed)

@bot.command(name='truth')
async def truth(ctx):
    """Get a random truth question."""
    await ctx.send(random.choice(TRUTH_QUESTIONS))

@bot.command(name='dare')
async def dare(ctx):
    """Get a random dare task."""
    await ctx.send(random.choice(DARE_TASKS))

@bot.command(name='flirt')
async def flirt(ctx):
    """Get a random pickup line."""
    await ctx.send(random.choice(PICKUP_LINES))

@bot.command(name='help')
async def help_command(ctx):
    """Show all available commands."""
    embed = discord.Embed(title="🍩 Sweet Holes Bot Commands", color=discord.Color.purple())
    embed.add_field(name="!points", value="Check your loyalty points and tier", inline=False)
    embed.add_field(name="!truth", value="Get a random truth question", inline=False)
    embed.add_field(name="!dare", value="Get a random dare challenge", inline=False)
    embed.add_field(name="!flirt", value="Get a random pickup line", inline=False)
    embed.add_field(name="!leaderboard", value="Show top 5 users by points", inline=False)
    embed.set_footer(text="Sweet Holes Bake Shop - Serving Sweetness & Sass 🍩💖")
    await ctx.send(embed=embed)

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    """Show top 5 users by points."""
    c.execute("SELECT user_id, points FROM rewards ORDER BY points DESC LIMIT 5")
    top_users = c.fetchall()
    
    embed = discord.Embed(title="🏆 Top Sweet Souls", color=discord.Color.gold())
    
    for idx, (user_id, points) in enumerate(top_users, 1):
        user = ctx.guild.get_member(user_id)
        name = user.name if user else f"User {user_id}"
        embed.add_field(name=f"#{idx} {name}", value=f"{points} points", inline=False)
    
    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    """Add points for active chatters."""
    if message.author.bot:
        return
        
    # Add 1 point for each message
    c.execute("INSERT OR REPLACE INTO rewards (user_id, points) VALUES (?, COALESCE((SELECT points + 1 FROM rewards WHERE user_id = ?), 1))", 
              (message.author.id, message.author.id))
    conn.commit()
    
    await bot.process_commands(message)

# Run bot with environment variable
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No Discord token found. Please set the DISCORD_TOKEN environment variable.")
    
bot.run(TOKEN)