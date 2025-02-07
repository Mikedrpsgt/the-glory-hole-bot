import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import sqlite3
import os
import asyncio

# Database Setup
conn = sqlite3.connect('orders.db')
c = conn.cursor()

# Create Tables
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item TEXT, quantity INTEGER, status TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS rewards 
             (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, loyalty_tier TEXT DEFAULT 'Tease')''')

c.execute('''CREATE TABLE IF NOT EXISTS vendors 
             (vendor_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, owner_id INTEGER, reward_description TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS redemptions 
             (redemption_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, vendor_id INTEGER, points_used INTEGER, status TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS feedback 
             (feedback_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, rating INTEGER, comment TEXT)''')

conn.commit()

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Business Admin Channel ID (Replace with actual channel ID)
ADMIN_CHANNEL_ID = 1337400405621211217  

# Brand Assets (Main Logo & Footer)
MAIN_LOGO_URL = "https://yourhost.com/main-logo.png"
FOOTER_IMAGE_URL = "https://yourhost.com/footer.png"

# Order Placement UI
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

# Feedback System
@bot.command()
async def feedback(ctx):
    """Request feedback from the user after an order is completed."""
    embed = discord.Embed(
        title="📢 Spill the Tea, Sugar!",
        description="Rate your experience with our *delicious* service. React below! 😘\n\n⭐ - 1 | ⭐⭐ - 2 | ⭐⭐⭐ - 3 | ⭐⭐⭐⭐ - 4 | ⭐⭐⭐⭐⭐ - 5",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=MAIN_LOGO_URL)
    message = await ctx.send(embed=embed)

    for i in range(1, 6):
        await message.add_reaction(f"{i}️⃣")

    def check(reaction, user):
        return user == ctx.author and reaction.message.id == message.id

    reaction, user = await bot.wait_for("reaction_add", check=check)
    rating = int(reaction.emoji[0])  

    await ctx.send("📋 **Oh honey, drop a little note about your experience!** 🥰")

    def comment_check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    msg = await bot.wait_for("message", check=comment_check)
    comment = msg.content

    c.execute("INSERT INTO feedback (user_id, rating, comment) VALUES (?, ?, ?)", (ctx.author.id, rating, comment))
    conn.commit()

    response = {
        1: "😢 Oh no, sugar! What did we do? Let me fix it. 🥺",
        2: "😕 Not quite love at first bite? We'll turn up the heat! 🔥",
        3: "😊 Decent, but we know you like it *better*. Next time, we’ll dazzle you. ✨",
        4: "😍 Ohhh, now we’re talking! We love to tease… and please. 😘",
        5: "🔥 You like it *hot*, huh? We LOVE that! You’re our favorite! 😏💖"
    }.get(rating, "🎉 Thanks, sweetheart! We love hearing from you! 💕")

    await ctx.send(f"✅ **Feedback saved!** {response}")

# Loyalty System (Flirty Tiers)
@tasks.loop(hours=24)
async def update_loyalty():
    """Upgrades users based on points."""
    c.execute("SELECT user_id, points FROM rewards")
    users = c.fetchall()

    for user_id, points in users:
        if points >= 100:
            new_tier = "🔥 Seductive Gold"
        elif points >= 50:
            new_tier = "💖 Passionate Silver"
        else:
            new_tier = "💋 Teasing Bronze"

        c.execute("UPDATE rewards SET loyalty_tier = ? WHERE user_id = ?", (new_tier, user_id))

    conn.commit()

@bot.command()
async def my_tier(ctx):
    """Check your loyalty tier."""
    user_id = ctx.author.id
    c.execute("SELECT loyalty_tier FROM rewards WHERE user_id = ?", (user_id,))
    result = c.fetchone()

    tier = result[0] if result else "💋 Teasing Bronze"
    await ctx.send(f"🏅 **Your Loyalty Tier:** {tier} - *Ooo, we love a committed customer!* 😏")

# Automated Reports
@tasks.loop(hours=24)
async def daily_report():
    """Daily business report."""
    await bot.wait_until_ready()
    
    # Get application owner
    app_info = await bot.application_info()
    owner = app_info.owner
    
    if not owner:
        print("❌ Error: Could not find bot owner")
        return

    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'Completed'")
    completed_orders = c.fetchone()[0]

    c.execute("SELECT SUM(points) FROM rewards")
    total_points = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM redemptions WHERE status = 'Approved'")
    total_redemptions = c.fetchone()[0]

    c.execute("SELECT AVG(rating) FROM feedback WHERE DATE('now', '-1 days') <= DATE('now')")
    avg_rating = c.fetchone()[0] or "No ratings yet"

    embed = discord.Embed(
        title="📊 Daily Business Report - Sweet & Spicy Edition 🔥",
        color=discord.Color.red()
    )
    embed.add_field(name="📦 Orders Fulfilled", value=f"**{completed_orders}** - Our customers are eating *good* 😘", inline=False)
    embed.add_field(name="🎁 Reward Points Earned", value=f"**{total_points}** - They love us, what can we say? 😏", inline=False)
    embed.add_field(name="🛍️ Redemptions Processed", value=f"**{total_redemptions}** - Who's getting spoiled? 😉", inline=False)
    embed.add_field(name="⭐ Customer Rating", value=f"**{avg_rating}** - We aim to please, baby! 😘", inline=False)
    embed.set_thumbnail(url=MAIN_LOGO_URL)
    embed.set_footer(text="Sweet Holes Bake Shop - Serving Sweetness & Sass 🍩💖", icon_url=FOOTER_IMAGE_URL)

    try:
        await owner.send(embed=embed)
    except discord.errors.Forbidden:
        print("❌ Error: Could not send DM to bot owner")

@bot.event
async def on_ready():
    daily_report.start()
    update_loyalty.start()
    print("🔥 Sweet Holes Bot is Live & Ready to Flirt! 😏")

# Run the bot
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)
