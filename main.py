import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import sqlite3
import os
import asyncio
import random
from datetime import datetime

# Database Setup & Auto Creation
def setup_database():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()

    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item TEXT, quantity INTEGER, status TEXT)''')

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
    "Sweet Silver": 50,
    "Seductive Gold": 100
}

class ApplicationModal(discord.ui.Modal, title="💖 Sweet Holes VIP Application"):
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
        placeholder="Tell us why you'd like to join Sweet Holes VIP...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not self.response_channel:
                await interaction.response.send_message("❌ Error: Application channel not found. Please contact an admin.", ephemeral=True)
                return
                
            embed = discord.Embed(
                title="✨ New VIP Application",
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
    if ctx.channel.id != 1337508682950377480:  # Rewards channel
        await ctx.send("❌ This command can only be used in the rewards channel!", ephemeral=True)
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
    user_id = interaction.user.id
    bonus_points = random.randint(5, 15)

    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("INSERT INTO rewards (user_id, points) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET points = points + ?", 
              (user_id, bonus_points, bonus_points))
    conn.commit()
    conn.close()

    await interaction.response.send_message(f"🎉 **Daily Reward Claimed!** You earned **+{bonus_points} points!** Keep coming back for more treats! 🍩")

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

@bot.tree.command(name="apply", description="Apply for Sweet Holes VIP")
async def apply(interaction: discord.Interaction):
    """Shows the application button interface."""
    response_channel = await bot.fetch_channel(1337645313279791174)
    if not response_channel:
        await interaction.response.send_message("Error: Could not find response channel!", ephemeral=True)
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
    
    apply_button = discord.ui.Button(label="😈 PROVE YOUR WORTH", style=discord.ButtonStyle.danger)
    apply_button.callback = apply_callback
    view.add_item(apply_button)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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

@bot.tree.command(name="add_vendor", description="Add a new vendor to rewards program")
@is_admin()
async def add_vendor(interaction: discord.Interaction, vendor_name: str, points_rate: int):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS vendors 
                 (vendor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT, points_rate INTEGER)''')

    c.execute("INSERT INTO vendors (name, points_rate) VALUES (?, ?)", 
              (vendor_name, points_rate))
    conn.commit()
    conn.close()

    await interaction.response.send_message(
        f"✅ Added vendor: {vendor_name} (Points Rate: {points_rate})",
        ephemeral=True
    )

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
async def on_ready():
    """Auto syncs commands and sends channel-specific messages on startup."""
    try:
        await bot.tree.sync()
        update_loyalty.start()
        print("🔥 Sweet Holes VIP & Flirty Fun Bot is LIVE! 😏")
        
        # Channel IDs
        apply_channel = bot.get_channel(1337508683286052894)
        response_channel = bot.get_channel(1337645313279791174)
        menu_channel = bot.get_channel(1337508682950377479)
        order_channel = bot.get_channel(1337508683286052899)
        tier_channel = bot.get_channel(1337508683684384846)

        # Set up apply button in apply channel first
        if apply_channel:
            await apply_channel.purge(limit=100)
            embed = discord.Embed(
                title="🔥 BECOME A SWEET HOLES GIGACHAD 🔥",
                description="Only the most based individuals may enter.\nProve your worth by clicking below.",
                color=discord.Color.purple()
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