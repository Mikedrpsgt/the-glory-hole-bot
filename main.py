import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import sqlite3
import os
import asyncio
import random
from datetime import datetime, timedelta

# Database Setup & Auto Creation
def setup_database():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()

    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item TEXT, quantity INTEGER, status TEXT, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS rewards 
                 (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, loyalty_tier TEXT DEFAULT 'Flirty Bronze',
                  last_daily TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS feedback 
                 (feedback_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, rating INTEGER, comment TEXT)''')

    conn.commit()
    conn.close()

setup_database()  # Ensures tables exist before the bot starts

# Bot Setup
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Admin role name
ADMIN_ROLE_NAME = "Sweet Holes Admin"

def is_admin():
    async def predicate(ctx):
        return discord.utils.get(ctx.author.roles, name=ADMIN_ROLE_NAME) is not None
    return commands.check(predicate)

# Brand Assets
MAIN_LOGO_URL = "https://yourhost.com/main-logo.png"
FOOTER_IMAGE_URL = "https://yourhost.com/footer.png"

# Loyalty Tiers & Perks
LOYALTY_TIERS = {
    "Flirty Bronze": 0,
    "Sweet Silver": 500,
    "Seductive Gold": 1000
}

class ApplicationModal(discord.ui.Modal, title="💖 Sweet Holes employee Application"):
    def __init__(self, response_channel):
        super().__init__()
        self.response_channel = response_channel

    name = discord.ui.TextInput(
        label="Your Name",
        placeholder="Enter your name",
        required=True
    )

    age = discord.ui.TextInput(
        label="Your Age",
        placeholder="Enter your age",
        required=True
    )

    why_join = discord.ui.TextInput(
        label="Why do you want to join?",
        style=discord.TextStyle.long,
        placeholder="Tell us why you'd like to join Sweet Holes team...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not self.response_channel:
                await interaction.response.send_message("❌ Error: Application channel not found. Please contact an admin.", ephemeral=True)
                return

            embed = discord.Embed(
                title="✨ New Employee Application",
                color=discord.Color.gold()
            )
            embed.add_field(name="Applicant", value=f"<@{interaction.user.id}>", inline=False)
            embed.add_field(name="Name", value=self.name.value, inline=True)
            embed.add_field(name="Age", value=self.age.value, inline=True)
            embed.add_field(name="Why Join", value=self.why_join.value, inline=False)

            await self.response_channel.send(embed=embed)
            await interaction.response.send_message("✅ Your application has been submitted! We'll review it soon.", ephemeral=True)
        except Exception as e:
            print(f"Application Error: {str(e)}")
            await interaction.response.send_message("❌ Something went wrong with your application. Please try again!", ephemeral=True)

# Fun Responses
PICKUP_LINES = [
    "Are you a donut? Because I’m totally glazed over you. 😉",
    "If sweetness was a crime, you’d be doing life, sugar. 😘",
    "Are you on the menu? Because I’d order you every time. 😏",
    "Do you have a map? I keep getting lost in your eyes. 🗺️",
    "Are you a magician? Because every time I look at you, everyone else disappears. 💫",
    "Are you a camera? Because every time I look at you, I smile. 📷",
    "Do you have a name? Or can I call you mine? 🤔",
    "Are you a library? Because I can't find you in any of my books. 📚",
    "Do you have a talent? Or can I borrow your camera lens? 📸",
    "Are you a bank? Because I can't help you with your money. 💰",
    "Do you have a hobby? Or can I borrow your camera lens? 📸",
    "Are you a ghost? Because I'm feeling spooky tonight. 👻",
    "Do you have a name? Or can I call you mine? 🤔",
    "Are you a camera? Because every time I look at you, I smile. 📷",
    "Do you have a name? Or can I call you mine? 🤔",
    "Are you a library? Because I can't find you in any of my books. 📚",
    "Do you have a talent? Or can I borrow your camera lens? 📸",
    "Are you a bank? Because I can't help you with your money. 💰",
    "Do you have a hobby? Or can I borrow your camera lens? 📸",
    "Are you a ghost? Because I'm feeling spooky tonight. 👻"
]

TRUTH_QUESTIONS = [
    "What's the sweetest thing someone has done for you? 🍯",
    "What’s your biggest guilty pleasure? (Besides me, obviously.) 😉",
    "What’s the most embarrassing thing you’ve ever done? 😬",
    "What’s the most childish thing you still do? 😜",
    "What’s the most embarrassing thing you’ve ever done in front of your crush? 😳",

]

DARE_TASKS = [
    "Send a 💋 emoji to the last person who ordered a donut. 😘",
    "Change your name to 'Sugar Daddy/Mommy' for 10 minutes. 🔥",
    "Send a 🍕 emoji to the last person who ordered a pizza. 🍕",
    "Change your name to 'Sweetie' for 10 minutes. 💖",
    "Send a 🍦 emoji to the last person who ordered a cupcake. 🍦",
    "Change your name to 'Sweetie' for 10 minutes. 💖",
    "Send a 🍦 emoji to the last person who ordered a cupcake. 🍦",
    "Change your name to 'Sweetie' for 10 minutes. 💖",
    "Send a 🍦 emoji to the last person who ordered a cupcake. 🍦",
]

# --- Order System ---
class OrderView(View):
    def __init__(self):
        super().__init__()

    class OrderModal(discord.ui.Modal, title="🍩 Place Your Order"):
        order_input = discord.ui.TextInput(
            label="What can I get you, sugar? 😘",
            placeholder="e.g., 2 glazed donuts and 1 chocolate eclair",
            style=discord.TextStyle.long,
            required=True
        )

        async def on_submit(self, interaction: discord.Interaction):
            try:
                order_text = self.order_input.value
                conn = sqlite3.connect('orders.db')
                c = conn.cursor()
                c.execute("INSERT INTO orders (user_id, item, quantity, status) VALUES (?, ?, ?, 'Pending')", 
                         (interaction.user.id, order_text, 1))
                conn.commit()
                order_id = c.lastrowid
                conn.close()

                embed = discord.Embed(
                    title="✅ Order Placed, Sweetheart!",
                    description=f"**Order ID:** `{order_id}`\n🍩 **Order:** {order_text}",
                    color=discord.Color.pink()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                await interaction.response.send_message("❌ Oops! Something went wrong with your order. Please try again!", ephemeral=True)

    @discord.ui.button(label="🍩 Place Order", style=discord.ButtonStyle.green)
    async def place_order(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(self.OrderModal())

    @discord.ui.button(label="📦 Check Status", style=discord.ButtonStyle.blurple)
    async def check_status(self, interaction: discord.Interaction, button: Button):
        user_id = interaction.user.id
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("SELECT order_id, item, quantity, status FROM orders WHERE user_id = ? ORDER BY order_id DESC LIMIT 5", (user_id,))
        orders = c.fetchall()
        conn.close()

        if not orders:
            await interaction.response.send_message("💔 No orders found, sweetie! Time to treat yourself? 😘", ephemeral=True)
            return

        embed = discord.Embed(title="🎀 Your Recent Orders", color=discord.Color.pink())
        for order in orders:
            embed.add_field(
                name=f"Order #{order[0]}",
                value=f"🍩 Item: {order[1]}\n📦 Quantity: {order[2]}\n📋 Status: {order[3]}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ Cancel Order", style=discord.ButtonStyle.red)
    async def cancel_order(self, interaction: discord.Interaction, button: Button):
        class CancelModal(discord.ui.Modal, title="Cancel Order"):
            order_id = discord.ui.TextInput(
                label="Order ID to Cancel",
                placeholder="Enter the order ID",
                required=True
            )

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    order_id = int(self.order_id.value)
                    conn = sqlite3.connect('orders.db')
                    c = conn.cursor()
                    c.execute("SELECT status FROM orders WHERE order_id = ? AND user_id = ?", 
                            (order_id, interaction.user.id))
                    order = c.fetchone()

                    if order:
                        if order[0] == 'Pending':
                            c.execute("DELETE FROM orders WHERE order_id = ? AND user_id = ?", 
                                    (order_id, interaction.user.id))
                            conn.commit()
                            await interaction.response.send_message(
                                f"💝 Order #{order_id} cancelled, darling!", 
                                ephemeral=True
                            )
                        else:
                            await interaction.response.send_message(
                                "❌ Sorry sweetie, you can only cancel pending orders!", 
                                ephemeral=True
                            )
                    else:
                        await interaction.response.send_message(
                            "❌ Order not found or not yours to cancel, sweetie!", 
                            ephemeral=True
                        )
                    conn.close()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ Please enter a valid order number, sugar!", 
                        ephemeral=True
                    )

        await interaction.response.send_modal(CancelModal())

class MenuView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="💋 Flirt", style=discord.ButtonStyle.danger)
    async def flirt(self, interaction: discord.Interaction, button: Button):
        line = random.choice(PICKUP_LINES)
        await interaction.response.send_message(f"💋 **Sweet Holes Flirty Line:** {line}", ephemeral=True)

    @discord.ui.button(label="💖 Truth", style=discord.ButtonStyle.primary)
    async def truth_button(self, interaction: discord.Interaction, button: Button):
        question = random.choice(TRUTH_QUESTIONS)
        await interaction.response.send_message(f"💖 **Truth:** {question}", ephemeral=True)

    @discord.ui.button(label="🔥 Dare", style=discord.ButtonStyle.danger)
    async def dare_button(self, interaction: discord.Interaction, button: Button):
        dare = random.choice(DARE_TASKS)
        await interaction.response.send_message(f"🔥 **Dare:** {dare}", ephemeral=True)

    @discord.ui.button(label="🎁 Daily Reward", style=discord.ButtonStyle.green)
    async def daily_reward(self, interaction: discord.Interaction, button: Button):
        try:
            user_id = interaction.user.id
            conn = sqlite3.connect('orders.db')
            c = conn.cursor()

            c.execute("SELECT last_daily, points FROM rewards WHERE user_id = ?", (user_id,))
            result = c.fetchone()

            current_time = datetime.now()
            if result and result[0]:
                last_claim = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                time_diff = current_time - last_claim

                if time_diff.total_seconds() < 86400:  # 24 hours in seconds
                    hours_left = 24 - (time_diff.total_seconds() / 3600)
                    await interaction.response.send_message(f"⏰ Hold up sweetie! You can claim again in {int(hours_left)} hours!", ephemeral=True)
                    conn.close()
                    return

            bonus_points = random.randint(5, 15)
            current_points = result[1] if result else 0

            c.execute("""INSERT INTO rewards (user_id, points, last_daily) 
                        VALUES (?, ?, ?) 
                        ON CONFLICT(user_id) DO UPDATE 
                        SET points = points + ?, last_daily = ?""", 
                     (user_id, bonus_points, current_time.strftime('%Y-%m-%d %H:%M:%S'), 
                      bonus_points, current_time.strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            conn.close()

            await interaction.response.send_message(
                f"🎉 **Daily Reward Claimed!** You earned **+{bonus_points} points!**\nTotal points: {current_points + bonus_points}", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message("❌ Something went wrong with the daily reward. Please try again!", ephemeral=True)
            if 'conn' in locals():
                conn.close()

    @discord.ui.button(label="💝 My Tier", style=discord.ButtonStyle.blurple)
    async def check_tier(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("SELECT loyalty_tier, points FROM rewards WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()

        tier, points = result if result else ("Flirty Bronze", 0)

        embed = discord.Embed(
            title="💖 Your VIP Sweet Holes Card 💖",
            description=f"👤 **{interaction.user.display_name}**\n🏅 **Tier:** {tier}\n🎁 **Points:** {points}",
            color=discord.Color.pink()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Loyalty System ---
@tasks.loop(hours=24)
async def update_loyalty():
    """Upgrades users based on points."""
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()

    c.execute("SELECT user_id, points FROM rewards")
    users = c.fetchall()

    for user_id, points in users:
        new_tier = "Flirty Bronze"
        for tier, min_points in LOYALTY_TIERS.items():
            if points >= min_points:
                new_tier = tier

        c.execute("UPDATE rewards SET loyalty_tier = ? WHERE user_id = ?", (new_tier, user_id))

    conn.commit()
    conn.close()

@bot.hybrid_command(name="menu", description="Show the interactive menu")
async def menu(ctx):
    """Shows the interactive menu with buttons."""
    if ctx.channel.id != 1337692528509456414:  # Menu channel
        await ctx.send("❌ This command can only be used in the menu channel!", ephemeral=True)
        return
    embed = discord.Embed(
        title="🎀 Sweet Holes Interactive Menu 🎀",
        description="Click the buttons below to interact!",
        color=discord.Color.pink()
    )
    await ctx.send(embed=embed, view=MenuView(), ephemeral=True)

@bot.hybrid_command(name="order", description="Show the order menu")
async def order(ctx):
    """Shows the order menu with buttons."""
    if ctx.channel.id != 1337508683286052899:  # Orders channel
        await ctx.send("❌ This command can only be used in the orders channel!", ephemeral=True)
        return
    embed = discord.Embed(
        title="🍩 Sweet Holes Order System 🍩",
        description="What can we get for you today, sugar? 😘",
        color=discord.Color.pink()
    )
    await ctx.send(embed=embed, view=OrderView(), ephemeral=True)

@bot.tree.command(name="my_tier", description="Check your loyalty tier")
async def my_tier(interaction: discord.Interaction):
    if interaction.channel_id != 1337508683684384846:  # Check tier channel
        await interaction.response.send_message("❌ This command can only be used in the check tier channel!", ephemeral=True)
        return
    """Check your loyalty tier."""
    user_id = interaction.user.id
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT loyalty_tier, points FROM rewards WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()

    tier, points = result if result else ("Flirty Bronze", 0)

    embed = discord.Embed(
        title="💖 Your VIP Sweet Holes Card 💖",
        description=f"👤 **{interaction.user.display_name}**\n🏅 **Loyalty Tier:** {tier}\n🎁 **Total Points:** {points}",
        color=discord.Color.pink()
    )
    embed.set_thumbnail(url=MAIN_LOGO_URL)
    embed.set_footer(text="Stay sweet, sugar! More rewards coming your way! 😘", icon_url=FOOTER_IMAGE_URL)

    await interaction.response.send_message(embed=embed)

# --- Fun Features ---
@bot.tree.command(name="pickup", description="Get a fun, flirty pick-up line")
async def pickup(interaction: discord.Interaction):
    """Sends a fun, flirty pick-up line."""
    line = random.choice(PICKUP_LINES)
    await interaction.response.send_message(f"💋 **Sweet Holes Flirty Line:** {line}", ephemeral=True)

@bot.tree.command(name="truth", description="Get a flirty truth question")
async def truth(interaction: discord.Interaction):
    """Gives a flirty truth question."""
    question = random.choice(TRUTH_QUESTIONS)
    await interaction.response.send_message(f"💖 **Truth:** {question}", ephemeral=True)

@bot.tree.command(name="dare", description="Get a fun dare task")
async def dare(interaction: discord.Interaction):
    """Gives a fun dare task."""
    dare = random.choice(DARE_TASKS)
    await interaction.response.send_message(f"🔥 **Dare:** {dare}", ephemeral=True)

@bot.tree.command(name="daily", description="Claim your daily bonus points")
async def daily(interaction: discord.Interaction):
    """Gives a daily bonus of points."""
    try:
        user_id = interaction.user.id
        bonus_points = random.randint(5, 15)

        conn = sqlite3.connect('orders.db')
        c = conn.cursor()

        # Check if user exists in rewards table
        c.execute("SELECT last_daily FROM rewards WHERE user_id = ?", (user_id,))
        last_claim = c.fetchone()

        if last_claim and last_claim[0]:
            last_time = datetime.strptime(last_claim[0], '%Y-%m-%d %H:%M:%S')
            if datetime.now() - last_time < timedelta(days=1):
                await interaction.response.send_message("❌ You've already claimed your daily reward! Try again tomorrow!", ephemeral=True)
                conn.close()
                return

        c.execute("""INSERT INTO rewards (user_id, points, last_daily) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(user_id) DO UPDATE 
                    SET points = points + ?, last_daily = ?""",
                 (user_id, bonus_points, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  bonus_points, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"🎉 **Daily Reward Claimed!** You earned **+{bonus_points} points!**")
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        await interaction.response.send_message("❌ Something went wrong! Please try again.", ephemeral=True)

# --- Auto Register Commands ---
# Admin Commands
class AdminView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="📝 Update Order", style=discord.ButtonStyle.blurple)
    async def update_order_button(self, interaction: discord.Interaction, button: Button):
        if not discord.utils.get(interaction.user.roles, name=ADMIN_ROLE_NAME):
            await interaction.response.send_message("❌ You don't have permission to do this!", ephemeral=True)
            return
        modal = UpdateOrderModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🎁 Give Points", style=discord.ButtonStyle.green)
    async def give_points_button(self, interaction: discord.Interaction, button: Button):
        if not discord.utils.get(interaction.user.roles, name=ADMIN_ROLE_NAME):
            await interaction.response.send_message("❌ You don't have permission to do this!", ephemeral=True)
            return
        modal = GivePointsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View Orders", style=discord.ButtonStyle.grey)
    async def view_orders_button(self, interaction: discord.Interaction, button: Button):
        if not discord.utils.get(interaction.user.roles, name=ADMIN_ROLE_NAME):
            await interaction.response.send_message("❌ You don't have permission to do this!", ephemeral=True)
            return
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("SELECT * FROM orders ORDER BY order_id DESC LIMIT 10")
        orders = c.fetchall()
        conn.close()

        embed = discord.Embed(title="📋 All Orders", color=discord.Color.blue())
        for order in orders:
            embed.add_field(
                name=f"Order #{order[0]}",
                value=f"User: {order[1]}\nItem: {order[2]}\nQuantity: {order[3]}\nStatus: {order[4]}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

class UpdateOrderModal(discord.ui.Modal, title="📝 Update Order Status"):
    order_id = discord.ui.TextInput(
        label="Order ID",
        style=discord.TextStyle.short,
        placeholder="Enter order ID",
        required=True
    )
    status = discord.ui.TextInput(
        label="New Status",
        style=discord.TextStyle.short,
        placeholder="e.g., Completed, Processing, Cancelled",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            order_id = int(self.order_id.value)
            status = self.status.value

            conn = sqlite3.connect('orders.db')
            c = conn.cursor()
            c.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
            conn.commit()
            conn.close()

            await interaction.response.send_message(f"✅ Order #{order_id} status updated to: {status}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid order ID format", ephemeral=True)

class GivePointsModal(discord.ui.Modal, title="🎁 Give Points"):
    user_id = discord.ui.TextInput(
        label="User ID",
        style=discord.TextStyle.short,
        placeholder="Enter user ID",
        required=True
    )
    points = discord.ui.TextInput(
        label="Points",
        style=discord.TextStyle.short,
        placeholder="Enter points amount",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            points = int(self.points.value)

            conn = sqlite3.connect('orders.db')
            c = conn.cursor()
            c.execute("INSERT INTO rewards (user_id, points) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET points = points + ?",
                      (user_id, points, points))
            conn.commit()
            conn.close()

            await interaction.response.send_message(f"✅ Added {points} points to user {user_id}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid input format", ephemeral=True)

@bot.command()
@is_admin()
async def admin(ctx):
    """Shows admin control panel"""
    embed = discord.Embed(
        title="🔐 Admin Control Panel",
        description="Use the buttons below to manage orders and users",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=AdminView(), ephemeral=True)

@bot.tree.command(name="update_order", description="Update order status (Admin only)")
@is_admin()
async def update_order(interaction: discord.Interaction, order_id: int, status: str):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Order #{order_id} status updated to: {status}")

@bot.tree.command(name="give_points", description="Give points to a user (Admin only)")
@is_admin()
async def give_points(interaction: discord.Interaction, user_id: int, points: int):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("INSERT INTO rewards (user_id, points) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET points = points + ?",
              (user_id, points, points))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Added {points} points to user {user_id}")

@bot.tree.command(name="view_all_orders", description="View all orders (Admin only)")
@is_admin()
async def view_all_orders(interaction: discord.Interaction):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY order_id DESC LIMIT 10")
    orders = c.fetchall()
    conn.close()

    embed = discord.Embed(title="📋 All Orders", color=discord.Color.blue())
    for order in orders:
        embed.add_field(
            name=f"Order #{order[0]}",
            value=f"User: {order[1]}\nItem: {order[2]}\nQuantity: {order[3]}\nStatus: {order[4]}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="view_feedback", description="View the last 5 customer reviews")
@is_admin()
async def view_feedback(interaction: discord.Interaction):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT * FROM feedback ORDER BY feedback_id DESC LIMIT 5")
    reviews = c.fetchall()
    conn.close()

    embed = discord.Embed(title="💖 Customer Reviews", color=discord.Color.pink())
    for review in reviews:
        embed.add_field(
            name=f"Review #{review[0]}",
            value=f"Rating: {'⭐' * review[2]}\nComment: {review[3]}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="vip_apply", description="Apply for Sweet Holes VIP Membership")
async def vip_apply(interaction: discord.Interaction):
    """Shows the VIP application button interface."""
    try:
        # Check if command is used in correct channel
        if interaction.channel.id != 1337508682950377480:  # VIP Membership channel
            await interaction.response.send_message("❌ This command can only be used in the VIP membership channel!", ephemeral=True)
            return

        response_channel = bot.get_channel(1337646191994867772)  # Applications response channel
        if not response_channel:
            print(f"Error: Could not access response channel ID: 1337646191994867772")
            await interaction.response.send_message("Error: Could not access response channel! Please contact an admin.", ephemeral=True)
            return

        # Check bot permissions
        bot_member = interaction.guild.me
        required_permissions = ['send_messages', 'embed_links', 'attach_files']
        missing_permissions = [perm for perm in required_permissions 
                             if not getattr(response_channel.permissions_for(bot_member), perm, False)]

        if missing_permissions:
            await interaction.response.send_message(
                f"Error: Bot missing permissions in response channel: {', '.join(missing_permissions)}! Please contact an admin.", 
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🔥 BECOME A SWEET HOLES GIGACHAD 🔥",
            description="Only the most based individuals may enter.\nProve your worth by clicking below.",
            color=discord.Color.purple()
        )
        view = discord.ui.View()

        async def apply_callback(button_interaction: discord.Interaction):
            modal = ApplicationModal(response_channel)
            await button_interaction.response.send_modal(modal)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
        return

    apply_button = discord.ui.Button(label="😈 PROVE YOUR WORTH", style=discord.ButtonStyle.danger)
    apply_button.callback = apply_callback
    view.add_item(apply_button)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="signup_rewards", description="Sign up for Sweet Holes rewards program")
async def signup_rewards(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        membership_channel = bot.get_channel(1337508682950377480)

        conn = sqlite3.connect('orders.db')
        c = conn.cursor()

        # Check if user already exists
        c.execute("SELECT points FROM rewards WHERE user_id = ?", (user_id,))
        existing_user = c.fetchone()

        if existing_user:
            await interaction.response.send_message("💝 You're already enrolled in our rewards program, sweetie!", ephemeral=True)
            conn.close()
            return

        # Add new user to rewards
        c.execute("INSERT INTO rewards (user_id, points, loyalty_tier) VALUES (?, ?, ?)", 
                 (user_id, 50, "Flirty Bronze"))
        conn.commit()
        conn.close()

        # Send welcome message to membership channel
        welcome_embed = discord.Embed(
            title="🎉 New Sweet Heart Joined!",
            description=f"Welcome <@{user_id}> to our VIP Rewards Program!\nStarting with 50 bonus points! 💖",
            color=discord.Color.pink()
        )
        await membership_channel.send(embed=welcome_embed)

        await interaction.response.send_message("✨ Welcome to Sweet Holes Rewards! You've earned 50 bonus points!", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message("❌ Something went wrong! Please try again.", ephemeralTrue)
        if 'conn' in locals():
            conn.close()

@bot.tree.command(name="vip_report", description="Generate VIP business report")
@is_admin()
async def vip_report(interaction: discord.Interaction):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()

    # Get today's orders
    c.execute("SELECT COUNT(*), SUM(quantity) FROM orders WHERE date(datetime('now'))")
    orders_data = c.fetchone()
    daily_orders = orders_data[0] or 0
    daily_items = orders_data[1] or 0

    # Get point redemptions
    c.execute("SELECT COUNT(*) FROM rewards WHERE points > 0")
    total_vip = c.fetchone()[0] or 0

    conn.close()

    embed = discord.Embed(title="📊 VIP Business Report", color=discord.Color.gold())
    embed.add_field(name="Daily Orders", value=str(daily_orders), inline=True)
    embed.add_field(name="Items Sold", value=str(daily_items), inline=True)
    embed.add_field(name="Total VIP Members", value=str(total_vip), inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="redeem", description="Redeem your Sweet Holes reward points")
async def redeem(interaction: discord.Interaction):
    if interaction.channel_id != 1337508683684384847:
        await interaction.response.send_message("❌ This command can only be used in the rewards redemption channel!", ephemeral=True)
        return

    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT points FROM rewards WHERE user_id = ?", (interaction.user.id,))
    result = c.fetchone()
    points = result[0] if result else 0
    conn.close()

    embed = discord.Embed(
        title="🎁 Sweet Holes Rewards Redemption",
        description=f"You have **{points}** points available!\nChoose a reward to redeem:",
        color=discord.Color.gold()
    )

    view = RedeemView(points)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class RedeemView(discord.ui.View):
    def __init__(self, points):
        super().__init__()
        self.points = points

    @discord.ui.button(label="🍩 Any Donut (150 points)", style=discord.ButtonStyle.primary)
    async def redeem_donut(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 150, "Any Donut")

    @discord.ui.button(label="🍦 Any Ice Cream (165 points)", style=discord.ButtonStyle.primary)
    async def redeem_ice_cream(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 165, "Any Ice Cream Scoop")

    @discord.ui.button(label="☕ Any Coffee (180 points)", style=discord.ButtonStyle.primary)
    async def redeem_coffee(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 180, "Any Coffee")

    @discord.ui.button(label="🥤 Any Milkshake (195 points)", style=discord.ButtonStyle.success)
    async def redeem_milkshake(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 195, "Any Milkshake")

    @discord.ui.button(label="🍪 Any Side (210 points)", style=discord.ButtonStyle.success)
    async def redeem_side(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 210, "Any Side")

    @discord.ui.button(label="🍩🍦 Any Cream Hole (225 points)", style=discord.ButtonStyle.success)
    async def redeem_cream_hole(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 225, "Any Cream Hole")

    @discord.ui.button(label="🥯 Breakfast Sammich (240 points)", style=discord.ButtonStyle.danger)
    async def redeem_breakfast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 240, "Any Breakfast Sammich")

    @discord.ui.button(label="🍽️ Free Meal (255 points)", style=discord.ButtonStyle.danger)
    async def redeem_meal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 255, "Free Meal Combo")

    @discord.ui.button(label="☕🔥 Unlimited Coffee Week (270 points)", style=discord.ButtonStyle.danger)
    async def redeem_coffee_week(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 270, "Week of Unlimited Coffee")

    @discord.ui.button(label="🍽️ Secret Menu Item (285 points)", style=discord.ButtonStyle.danger)
    async def redeem_secret(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 285, "VIP Secret Menu Item")

    @discord.ui.button(label="🍩 Month of Desserts (300 points)", style=discord.ButtonStyle.danger)
    async def redeem_dessert_month(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_redemption(interaction, 300, "Month of Free Desserts")

    @discord.ui.button(label="🎁 Vendor Rewards", style=discord.ButtonStyle.danger)
    async def redeem_vendor(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("SELECT * FROM vendor_rewards")
        rewards = c.fetchall()
        conn.close()
        
        if not rewards:
            await interaction.response.send_message("❌ No vendor rewards available!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="🏪 Available Vendor Rewards",
            description="Choose a reward to redeem:",
            color=discord.Color.gold()
        )
        
        for reward in rewards:
            embed.add_field(
                name=f"{reward[2]} ({reward[3]} points)",
                value=reward[4],
                inline=False
            )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def process_redemption(self, interaction: discord.Interaction, cost: int, item: str):
        if self.points < cost:
            await interaction.response.send_message(f"❌ Not enough points! You need {cost} points for {item}.", ephemeral=True)
            return

        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("UPDATE rewards SET points = points - ? WHERE user_id = ?", (cost, interaction.user.id))
        conn.commit()
        conn.close()

        # Send confirmation to user
        user_embed = discord.Embed(
            title="🎉 Reward Redeemed!",
            description=f"Successfully redeemed **{item}** for {cost} points!\nA staff member will contact you soon!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=user_embed, ephemeral=True)

        # Send notification to redemption log channel
        log_channel = interaction.client.get_channel(1337712800453230643)
        if log_channel:
            log_embed = discord.Embed(
                title="🎁 New Reward Redemption",
                description=f"**User:** {interaction.user.mention}\n**Item:** {item}\n**Cost:** {cost} points",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            await log_channel.send(embed=log_embed)

class VendorRewardModal(discord.ui.Modal, title="🏪 Add Vendor Reward"):
    reward_name = discord.ui.TextInput(
        label="Reward Name",
        placeholder="Enter the reward name",
        required=True
    )
    
    points_cost = discord.ui.TextInput(
        label="Points Cost",
        placeholder="Enter points required",
        required=True
    )
    
    description = discord.ui.TextInput(
        label="Description",
        style=discord.TextStyle.long,
        placeholder="Describe the reward...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            points = int(self.points_cost.value)
            
            conn = sqlite3.connect('orders.db')
            c = conn.cursor()
            
            # Create vendor rewards table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS vendor_rewards
                        (reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
                         vendor_id INTEGER,
                         reward_name TEXT,
                         points_cost INTEGER,
                         description TEXT)''')
            
            c.execute("INSERT INTO vendor_rewards (vendor_id, reward_name, points_cost, description) VALUES (?, ?, ?, ?)",
                     (interaction.user.id, self.reward_name.value, points, self.description.value))
            
            conn.commit()
            conn.close()
            
            embed = discord.Embed(
                title="✅ Vendor Reward Added",
                description=f"**{self.reward_name.value}**\nCost: {points} points\n{self.description.value}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Points cost must be a number!", ephemeral=True)

@bot.tree.command(name="vendor_add", description="Add vendor rewards to the redemption system")
async def vendor_add(interaction: discord.Interaction):
    # Check if user has vendor role
    if not any(role.name == "Vendor" for role in interaction.user.roles):
        await interaction.response.send_message("❌ You need the Vendor role to use this command!", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="🏪 Add Vendor Reward",
        description="Click the button below to add a new reward to the redemption system",
        color=discord.Color.blue()
    )
    
    view = discord.ui.View()
    add_button = discord.ui.Button(label="➕ Add Reward", style=discord.ButtonStyle.primary)
    
    async def button_callback(interaction: discord.Interaction):
        await interaction.response.send_modal(VendorRewardModal())
        
    add_button.callback = button_callback
    view.add_item(add_button)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="add_points", description="Add points to a user")
@is_admin()
async def add_points(interaction: discord.Interaction, user: discord.Member, points: int):
    """Add points to a user's balance."""
    try:
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        
        c.execute("""INSERT INTO rewards (user_id, points) 
                     VALUES (?, ?) 
                     ON CONFLICT(user_id) 
                     DO UPDATE SET points = points + ?""", 
                  (user.id, points, points))
        
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="✅ Points Added",
            description=f"Added {points} points to {user.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="remove_points", description="Remove points from a user")
@is_admin()
async def remove_points(interaction: discord.Interaction, user: discord.Member, points: int):
    """Remove points from a user's balance."""
    try:
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        
        # Check current points
        c.execute("SELECT points FROM rewards WHERE user_id = ?", (user.id,))
        result = c.fetchone()
        
        if not result:
            await interaction.response.send_message("❌ User has no points!", ephemeral=True)
            return
            
        current_points = result[0]
        if current_points < points:
            await interaction.response.send_message("❌ User doesn't have enough points!", ephemeral=True)
            return
            
        c.execute("UPDATE rewards SET points = points - ? WHERE user_id = ?", (points, user.id))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="✅ Points Removed",
            description=f"Removed {points} points from {user.mention}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="remove_vendor_reward", description="Remove a vendor reward")
@is_admin()
async def remove_vendor_reward(interaction: discord.Interaction):
    """Remove a vendor reward from the system."""
    if interaction.channel_id != 1337508683684384847:  # Redeem channel
        await interaction.response.send_message("❌ This command can only be used in the rewards redemption channel!", ephemeral=True)
        return

    try:
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        
        # Get all rewards for display
        c.execute("SELECT reward_id, reward_name, points_cost FROM vendor_rewards")
        rewards = c.fetchall()
        
        if not rewards:
            await interaction.response.send_message("❌ No vendor rewards found!", ephemeral=True)
            return
            
        # Create dropdown menu
        class RewardSelect(discord.ui.Select):
            def __init__(self):
                options = [
                    discord.SelectOption(
                        label=f"{reward[1]} ({reward[2]} points)",
                        value=str(reward[0]),
                        description=f"ID: {reward[0]}"
                    ) for reward in rewards
                ]
                super().__init__(
                    placeholder="Select a reward to remove...",
                    options=options
                )

            async def callback(self, interaction: discord.Interaction):
                reward_id = int(self.values[0])
                
                conn = sqlite3.connect('orders.db')
                c = conn.cursor()
                c.execute("DELETE FROM vendor_rewards WHERE reward_id = ?", (reward_id,))
                conn.commit()
                conn.close()
                
                embed = discord.Embed(
                    title="✅ Vendor Reward Removed",
                    description=f"Successfully removed reward ID: {reward_id}",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        # Create view with dropdown
        view = discord.ui.View()
        view.add_item(RewardSelect())
        
        embed = discord.Embed(
            title="🗑️ Remove Vendor Reward",
            description="Select a reward to remove from the system:",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        conn.close()
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="update_loyalty", description="Manually update customer loyalty tiers")
@is_admin()
async def manual_update_loyalty(interaction: discord.Interaction):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()

    c.execute("SELECT user_id, points FROM rewards")
    users = c.fetchall()
    updated = 0

    for user_id, points in users:
        new_tier = "Flirty Bronze"
        for tier, min_points in LOYALTY_TIERS.items():
            if points >= min_points:
                new_tier = tier

        c.execute("UPDATE rewards SET loyalty_tier = ? WHERE user_id = ?", 
                  (new_tier, user_id))
        updated += 1

    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ Updated loyalty tiers for {updated} users", 
        ephemeral=True
    )

@bot.event
async def on_member_join(member):
    """Sends a welcome message when a new member joins."""
    welcome_channel = bot.get_channel(1337508682950377473)
    if welcome_channel:
        embed = discord.Embed(
            title="👋 Welcome to Sweet Holes!",
            description=f"Hey {member.mention}! Welcome to our sweet community! 🍩\n\nMake sure to check out our rewards program and VIP membership!",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await welcome_channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    """Sends a goodbye message when a member leaves."""
    goodbye_channel = bot.get_channel(1337508682950377476)
    if goodbye_channel:
        embed = discord.Embed(
            title="👋 Farewell!",
            description=f"Goodbye {member.name}! We hope to see you again soon! 🍩",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await goodbye_channel.send(embed=embed)

# Message XP cooldown tracking
message_cooldowns = {}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Process commands if any
    await bot.process_commands(message)
    
    # Check cooldown (1 minute between point rewards)
    user_id = message.author.id
    current_time = datetime.now()
    if user_id in message_cooldowns:
        if (current_time - message_cooldowns[user_id]).total_seconds() < 60:
            return
    
    # Award points for activity
    points = random.randint(1, 3)  # Random points between 1-3
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    
    c.execute("""INSERT INTO rewards (user_id, points) 
                 VALUES (?, ?) 
                 ON CONFLICT(user_id) 
                 DO UPDATE SET points = points + ?""", 
              (user_id, points, points))
    
    conn.commit()
    conn.close()
    
    # Update cooldown
    message_cooldowns[user_id] = current_time

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
        
    # Award points for reactions
    points = 1
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    
    c.execute("""INSERT INTO rewards (user_id, points) 
                 VALUES (?, ?) 
                 ON CONFLICT(user_id) 
                 DO UPDATE SET points = points + ?""", 
              (user.id, points, points))
    
    conn.commit()
    conn.close()

@bot.event
async def on_ready():
    """Auto syncs commands and sends channel-specific messages on startup."""
    try:
        # Verify database integrity
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()

        # Ensure all tables exist with correct schema
        c.execute('''CREATE TABLE IF NOT EXISTS orders 
                     (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                      item TEXT, quantity INTEGER, status TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS rewards
                     (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0,
                      loyalty_tier TEXT DEFAULT 'Flirty Bronze', last_daily TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS feedback
                     (feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER, rating INTEGER, comment TEXT)''')

        conn.commit()
        conn.close()

        await bot.tree.sync()
        update_loyalty.start()
        print("🔥 Sweet Holes VIP & Flirty Fun Bot is LIVE! 😏")

        # Channel IDs
        apply_channel = bot.get_channel(1337508683286052894)
        response_channel = bot.get_channel(1337645313279791174)
        menu_channel = bot.get_channel(1337692528509456414)
        order_channel = bot.get_channel(1337508683286052899)
        tier_channel = bot.get_channel(1337508683684384846)
        membership_channel = bot.get_channel(1337508682950377480)

        # Set up VIP application button in membership channel
        if membership_channel:
            await membership_channel.purge(limit=100)
            embed = discord.Embed(
                title="💎 SWEET HOLES VIP MEMBERSHIP 💎",
                description="Join our exclusive VIP program and unlock special perks!\nApply now by clicking below.",
                color=discord.Color.gold()
            )
            view = discord.ui.View()

            async def apply_callback(interaction: discord.Interaction):
                modal = ApplicationModal(response_channel)
                await interaction.response.send_modal(modal)

            apply_button = discord.ui.Button(label="😈 PROVE YOUR WORTH", style=discord.ButtonStyle.danger)
            apply_button.callback = apply_callback
            view.add_item(apply_button)
            await apply_channel.send(embed=embed, view=view)

        # Clear existing messages and send new ones
        if menu_channel:
            await menu_channel.purge(limit=100)
            embed = discord.Embed(
                title="🎀 Sweet Holes Interactive Menu 🎀",
                description="Click the buttons below to interact!",
                color=discord.Color.pink()
            )
            await menu_channel.send(embed=embed, view=MenuView())

        if order_channel:
            await order_channel.purge(limit=100)
            embed = discord.Embed(
                title="🍩 Sweet Holes Order System 🍩",
                description="What can we get for you today, sugar? 😘",
                color=discord.Color.pink()
            )
            await order_channel.send(embed=embed, view=OrderView())

        if tier_channel:
            await tier_channel.purge(limit=100)
            embed = discord.Embed(
                title="💖 Check Your VIP Status 💖",
                description="Click the button below to check your tier and points!",
                color=discord.Color.pink()
            )
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="💝 Check My Tier", style=discord.ButtonStyle.blurple, custom_id="check_tier"))
            await tier_channel.send(embed=embed, view=view)

        if membership_channel:
            await membership_channel.purge(limit=100)
            embed = discord.Embed(
                title="💎 Sweet Holes Membership",
                description="Welcome to our exclusive membership area!",
                color=discord.Color.gold()
            )
            await membership_channel.send(embed=embed)

        # Initialize VIP application button in membership channel
        vip_channel = bot.get_channel(1337508682950377480)
        if vip_channel:
            await vip_channel.purge(limit=100)
            embed = discord.Embed(
                title="💎 SWEET HOLES VIP MEMBERSHIP 💎",
                description="Join our exclusive VIP program and unlock special perks!",
                color=discord.Color.gold()
            )
            view = discord.ui.View()
            vip_button = discord.ui.Button(label="🌟 Apply for VIP", style=discord.ButtonStyle.danger)
            
            async def vip_callback(interaction: discord.Interaction):
                if interaction.channel.id != 1337508682950377480:
                    await interaction.response.send_message("❌ Wrong channel!", ephemeral=True)
                    return
                await vip_apply(interaction)
                
            vip_button.callback = vip_callback
            view.add_item(vip_button)
            await vip_channel.send(embed=embed, view=view)

        # Initialize job application button
        job_channel = bot.get_channel(1337508683286052894)
        if job_channel:
            await job_channel.purge(limit=100)
            embed = discord.Embed(
                title="💼 SWEET HOLES EMPLOYMENT 💼",
                description="Join our amazing team! Click below to apply.",
                color=discord.Color.blue()
            )
            view = discord.ui.View()
            job_button = discord.ui.Button(label="📝 Apply Now", style=discord.ButtonStyle.primary)
            
            async def job_callback(interaction: discord.Interaction):
                if interaction.channel.id != 1337508683286052894:
                    await interaction.response.send_message("❌ Wrong channel!", ephemeral=True)
                    return
                await apply(interaction)
                
            job_button.callback = job_callback
            view.add_item(job_button)
            await job_channel.send(embed=embed, view=view)

        # Initialize redeem command in rewards channel
        redeem_channel = bot.get_channel(1337508683684384847)
        if redeem_channel:
            await redeem_channel.purge(limit=100)
            embed = discord.Embed(
                title="🎁 Sweet Holes Rewards Redemption",
                description="Click below to redeem your reward points!",
                color=discord.Color.gold()
            )
            view = discord.ui.View()
            redeem_button = discord.ui.Button(label="🎁 Redeem Points", style=discord.ButtonStyle.success)
            
            async def redeem_callback(interaction: discord.Interaction):
                if interaction.channel.id != 1337508683684384847:
                    await interaction.response.send_message("❌ Wrong channel!", ephemeral=True)
                    return
                await redeem(interaction)
                
            redeem_button.callback = redeem_callback
            view.add_item(redeem_button)
            await redeem_channel.send(embed=embed, view=view)

        # Initialize vendor command in vendor channel
        vendor_channel = bot.get_channel(1337705856061407283)
        if vendor_channel:
            await vendor_channel.purge(limit=100)
            embed = discord.Embed(
                title="🏪 Vendor Reward Management",
                description="Click below to add or manage your vendor rewards!",
                color=discord.Color.blue()
            )
            view = discord.ui.View()
            vendor_button = discord.ui.Button(label="➕ Add Vendor Reward", style=discord.ButtonStyle.primary)
            
            async def vendor_callback(interaction: discord.Interaction):
                if interaction.channel.id != 1337705856061407283:
                    await interaction.response.send_message("❌ Wrong channel!", ephemeral=True)
                    return
                await vendor_add(interaction)
                
            vendor_button.callback = vendor_callback
            view.add_item(vendor_button)
            await vendor_channel.send(embed=embed, view=view)

        # Verify database tables
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        tables = ['orders', 'rewards', 'feedback']
        for table in tables:
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not c.fetchone():
                print(f"⚠️ Warning: Table '{table}' not found!")
        conn.close()
    except Exception as e:
        print(f"❌ Startup Error: {str(e)}")

# Run the bot
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)