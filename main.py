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
                new
