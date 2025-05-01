import discord
from discord import app_commands
from discord.ext import commands
from discord import Interaction
from datetime import datetime, timedelta
from discord import ui
import datetime
import psutil
import random, datetime, matplotlib.pyplot as plt, asyncio, os
import matplotlib.dates as mdates
import mysql.connector
import secrets
import string
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)
logger = logging.getLogger(__name__)

MAX_SUPPLY = 1_000_000
DEFAULT_CATEGORY_NAME = "Private Mines"

def get_connection():
    return mysql.connector.connect(
        host="15.235.149.195",
        user="u27_q3uxwnoUyF",
        password="sE5bG!g3k5W+=TahGumV+kSh",
        database="s27_bootmine"
    )

def init_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS server_config (
        server_id VARCHAR(32) PRIMARY KEY,
        private_mine_category VARCHAR(100)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(32) PRIMARY KEY,
        balance DOUBLE DEFAULT 0,
        rig INT DEFAULT 0,
        bought DOUBLE DEFAULT 0,
        sold DOUBLE DEFAULT 0,
        last_claim DATETIME NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_server_wallets (
        user_id VARCHAR(32),
        server_id VARCHAR(32),
        balance DOUBLE DEFAULT 0,
        rig INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, server_id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS private_mine_channels (
        channel_id VARCHAR(32) PRIMARY KEY,
        user_id VARCHAR(32),
        server_id VARCHAR(32),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS private_wallets (
        user_id VARCHAR(32),
        password VARCHAR(64) PRIMARY KEY,
        balance DOUBLE DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        timestamp DATETIME,
        price DOUBLE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS global_data (
        key_name VARCHAR(50) PRIMARY KEY,
        value DOUBLE
    )
    """)
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (id, balance, rig, bought, sold, last_claim) VALUES (%s, 0, 0, 0, 0, NULL)", (user_id,))
        conn.commit()
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
    if "last_claim" not in user:
        user["last_claim"] = None
    conn.close()
    return user

def update_user_data(user):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users SET balance = %s, rig = %s, bought = %s, sold = %s, last_claim = %s WHERE id = %s
    """, (user['balance'], user['rig'], user['bought'], user['sold'], user.get("last_claim"), user['id']))
    conn.commit()
    conn.close()

def get_server_data(server_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS server_wallets (
                server_id VARCHAR(32) PRIMARY KEY,
                balance DOUBLE DEFAULT 0,
                rig INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("SELECT * FROM server_wallets WHERE server_id = %s", (server_id,))
        server = cur.fetchone()
        
        if not server:
            cur.execute("""
                INSERT INTO server_wallets (server_id, balance, rig)
                VALUES (%s, 0, 0)
            """, (server_id,))
            conn.commit()
            cur.execute("SELECT * FROM server_wallets WHERE server_id = %s", (server_id,))
            server = cur.fetchone()
        
        return server
        
    except Exception as e:
        print(f"Error in get_server_data: {str(e)}")
        raise
    finally:
        conn.close()

def update_server_data(server_id, balance=None, rig=None):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        if rig is not None:
            cur.execute("""
                INSERT INTO server_wallets (server_id, rig) 
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE rig = rig + %s
            """, (server_id, rig, rig))
        
        if balance is not None:
            cur.execute("""
                INSERT INTO server_wallets (server_id, balance) 
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE balance = %s
            """, (server_id, balance, balance))
        
        conn.commit()
    except Exception as e:
        print(f"Error updating server data: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_market_price():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM global_data WHERE key_name = 'market_price'")
    result = cur.fetchone()
    if result:
        return float(result[0])
    cur.execute("INSERT INTO global_data (key_name, value) VALUES ('market_price', 1.0)")
    conn.commit()
    conn.close()
    return 1.0

def set_market_price(price):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO global_data (key_name, value) VALUES ('market_price', %s)
        ON DUPLICATE KEY UPDATE value = %s
    """, (price, price))
    conn.commit()
    conn.close()

def append_price_history(price):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO price_history (timestamp, price) VALUES (%s, %s)", (datetime.datetime.utcnow(), price))
    conn.commit()
    conn.close()

def generate_price_graph():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT timestamp, price FROM price_history ORDER BY timestamp DESC LIMIT 100")
    data = cur.fetchall()
    conn.close()

    if not data:
        return None

    timestamps = [row[0] for row in data][::-1]
    prices = [row[1] for row in data][::-1]

    plt.figure(figsize=(8, 4))
    plt.plot(timestamps, prices, marker='o', linestyle='-', color='gold')
    plt.title("Grafik Pertumbuhan Harga Coin")
    plt.xlabel("Waktu")
    plt.ylabel("Harga Coin")
    plt.grid(True)
    plt.tight_layout()
    plt.gcf().autofmt_xdate()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

    image_path = "data/coin_graph.png"
    os.makedirs("data", exist_ok=True)
    plt.savefig(image_path)
    plt.close()
    return image_path

def get_total_mined():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM global_data WHERE key_name = 'total_mined'")
    result = cur.fetchone()
    if result:
        return float(result[0])
    cur.execute("INSERT INTO global_data (key_name, value) VALUES ('total_mined', 0)")
    conn.commit()
    conn.close()
    return 0.0

def set_total_mined(value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO global_data (key_name, value) VALUES ('total_mined', %s)
        ON DUPLICATE KEY UPDATE value = %s
    """, (value, value))
    conn.commit()
    conn.close()

def generate_wallet_password():
    parts = [''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)) for _ in range(4)]
    return '-'.join(parts)

def create_private_wallet(user_id):
    """Membuat wallet baru dengan password unik"""
    password = generate_wallet_password()
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM private_wallets WHERE user_id = %s", (user_id,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return None
    cur.execute("INSERT INTO private_wallets (user_id, password, balance) VALUES (%s, %s, 0)", 
               (user_id, password))
    conn.commit()
    wallet = get_private_wallet(password)
    
    cur.close()
    conn.close()
    return wallet

def get_user_wallets(user_id):
    """Mendapatkan semua wallet milik user"""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM private_wallets WHERE user_id = %s", (user_id,))
    wallets = cur.fetchall()
    conn.close()
    return wallets

def get_private_wallet(password):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM private_wallets WHERE password = %s", (password,))
    wallet = cur.fetchone()
    cur.close()
    conn.close()
    return wallet

def update_wallet_balance(password, new_balance):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE private_wallets SET balance = %s WHERE password = %s", (new_balance, password))
    conn.commit()
    cur.close()
    conn.close()

def create_user_server_wallet(user_id, server_id):
    """Membuat wallet server baru untuk pengguna di server tertentu"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO user_server_wallets (user_id, server_id, balance, rig)
            VALUES (%s, %s, 0, 0)
        """, (user_id, server_id))
        conn.commit()
        cur.execute("SELECT * FROM user_server_wallets WHERE user_id = %s AND server_id = %s", (user_id, server_id))
        wallet = cur.fetchone()
        return {
            "user_id": wallet[0],
            "server_id": wallet[1],
            "balance": wallet[2],
            "rig": wallet[3],
            "created_at": wallet[4]
        }
    except Exception as e:
        conn.rollback()
        print(f"Error creating user server wallet: {str(e)}")
        return None
    finally:
        conn.close()

def get_user_server_wallet(user_id, server_id):
    """Mendapatkan data wallet server pengguna"""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM user_server_wallets WHERE user_id = %s AND server_id = %s", (user_id, server_id))
    wallet = cur.fetchone()
    conn.close()
    return wallet

def update_user_server_wallet(user_id, server_id, balance=None, rig=None):
    """Memperbarui data wallet server pengguna"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        if balance is not None:
            cur.execute("""
                UPDATE user_server_wallets
                SET balance = %s
                WHERE user_id = %s AND server_id = %s
            """, (balance, user_id, server_id))
        if rig is not None:
            cur.execute("""
                UPDATE user_server_wallets
                SET rig = %s
                WHERE user_id = %s AND server_id = %s
            """, (rig, user_id, server_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error updating user server wallet: {str(e)}")
        raise
    finally:
        conn.close()
    
def create_private_mine_channel(channel_id, user_id, server_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO private_mine_channels (channel_id, user_id, server_id)
            VALUES (%s, %s, %s)
        """, (channel_id, user_id, server_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating private mine channel: {str(e)}")
        return False
    finally:
        conn.close()

def get_private_mine_channel(channel_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM private_mine_channels WHERE channel_id = %s", (channel_id,))
    channel = cur.fetchone()
    conn.close()
    return channel

def delete_private_mine_channel(channel_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM private_mine_channels WHERE channel_id = %s", (channel_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting private mine channel: {str(e)}")
        return False
    finally:
        conn.close()

def get_category_name(server_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT private_mine_category FROM server_config WHERE server_id = %s", (server_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else DEFAULT_CATEGORY_NAME

def set_category_name(server_id, category_name):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO server_config (server_id, private_mine_category)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE private_mine_category = %s
        """, (server_id, category_name, category_name))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error setting category name: {str(e)}")
        return False
    finally:
        conn.close()

def create_private_mine_channel(channel_id, user_id, server_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO private_mine_channels (channel_id, user_id, server_id)
            VALUES (%s, %s, %s)
        """, (channel_id, user_id, server_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating private mine channel: {str(e)}")
        return False
    finally:
        conn.close()

def get_private_mine_channel(channel_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM private_mine_channels WHERE channel_id = %s", (channel_id,))
    channel = cur.fetchone()
    conn.close()
    return channel

def safe_get(data, key, default=None):
    """Helper function untuk menghindari NoneType error"""
    if not data:
        return default
    return data.get(key, default)

class DeletePrivateMineButton(ui.View):
    def __init__(self, channel_id: str, user_id: str, server_id: str):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.user_id = user_id
        self.server_id = server_id

    @ui.button(label="Hapus Channel", style=discord.ButtonStyle.danger, custom_id="delete_private_mine")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Hanya pemilik channel atau admin yang bisa menghapus channel ini.", ephemeral=True)
            return
        channel_data = get_private_mine_channel(self.channel_id)
        if not channel_data:
            await interaction.response.send_message("❌ Channel ini tidak lagi terdaftar sebagai private mine.", ephemeral=True)
            return

        try:
            channel = interaction.guild.get_channel(int(self.channel_id))
            if channel:
                await channel.delete(reason=f"Private mine channel dihapus oleh {interaction.user.name}")

            if delete_private_mine_channel(self.channel_id):
                await interaction.response.send_message("✅ Channel private mine berhasil dihapus.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Gagal menghapus data channel dari database.", ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot tidak memiliki izin untuk menghapus channel.", ephemeral=True)
        except Exception as e:
            print(f"Error deleting private mine channel: {str(e)}")
            await interaction.response.send_message("❌ Terjadi kesalahan saat menghapus channel.", ephemeral=True)

class CoinSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mining_users = set()
    async def buat_wallet_server(self, interaction: discord.Interaction):
        pass

    async def add_rig_to_server(self, interaction: discord.Interaction, jumlah: int):
        pass

    async def server_mine(self, interaction: discord.Interaction):
        pass

    async def wallet_server(self, interaction: discord.Interaction):
        pass
    class DeletePrivateMineButton(ui.View):
        def __init__(self, channel_id: str, user_id: str, server_id: str):
            super().__init__(timeout=None)
            self.channel_id = channel_id
            self.user_id = user_id
            self.server_id = server_id

        @ui.button(label="Hapus Channel", style=discord.ButtonStyle.danger, custom_id="delete_private_mine")
        async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            pass
        
    async def buat_private_mine(self, interaction: discord.Interaction):
        pass

    async def private_mine(self, interaction: discord.Interaction):
        pass  # TODO: 

    async def hapus_private_mine(self, interaction: discord.Interaction):
        pass

    def __init__(self, bot):
        self.bot = bot
        self.mining_users = set() 

    @app_commands.command(name="set_private_mine_category", description="Set category untuk private mine (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_private_mine_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        server_id = str(interaction.guild.id)
        category_name = category.name

        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Bot tidak memiliki izin untuk mengatur channel.", ephemeral=True)
            return

        if set_category_name(server_id, category_name):
            try:
                max_position = max([c.position for c in interaction.guild.categories])
                if category.position != max_position:
                    await category.edit(position=max_position, reason="Memindahkan category private mine ke paling bawah")
            except discord.Forbidden:
                await interaction.response.send_message(
                    "✅ Category diset, tapi bot tidak bisa memindahkan ke posisi paling bawah karena kurang izin.",
                    ephemeral=True
                )
                return
            except Exception as e:
                logger.error(f"Error moving category: {str(e)}")
                await interaction.response.send_message(
                    "✅ Category diset, tapi gagal memindahkan ke posisi paling bawah.",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"✅ Category untuk private mine diset ke '{category_name}'.", ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Gagal menyimpan pengaturan category.", ephemeral=True)

    @app_commands.command(name="buat_private_mine", description="Buat channel private mine yang hanya bisa dilihat olehmu dan admin")
    async def buat_private_mine(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return

        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.manage_channels or not bot_member.guild_permissions.manage_permissions:
            await interaction.response.send_message("❌ Bot tidak memiliki izin untuk membuat atau mengatur channel.", ephemeral=True)
            return

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT channel_id FROM private_mine_channels WHERE user_id = %s AND server_id = %s", (user_id, server_id))
        existing_channel = cur.fetchone()
        conn.close()

        if existing_channel:
            await interaction.response.send_message("❌ Kamu sudah memiliki channel private mine di server ini.", ephemeral=True)
            return

        try:
            guild = interaction.guild
            everyone_role = guild.default_role
            creator = guild.get_member(int(user_id))

            category_name = get_category_name(server_id)
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                max_position = max([c.position for c in guild.categories], default=-1) + 1
                category = await guild.create_category(
                    name=category_name,
                    reason="Category untuk private mine channels",
                    position=max_position
                )
            else:
                max_position = max([c.position for c in guild.categories])
                if category.position != max_position:
                    await category.edit(position=max_position, reason="Memindahkan category private mine ke paling bawah")
            overwrites = {
                everyone_role: discord.PermissionOverwrite(view_channel=False),
                creator: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
            }
            for role in guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )
            channel_name = f"private-mine-{creator.name}"
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Private mine channel untuk {creator.name}"
            )
            if not create_private_mine_channel(str(channel.id), user_id, server_id):
                await channel.delete()
                await interaction.response.send_message("❌ Gagal menyimpan channel ke database.", ephemeral=True)
                return
            embed = discord.Embed(
                title="🎉 Selamat Datang di Private Mine!",
                description=(
                    f"Channel ini hanya bisa dilihat olehmu dan admin server.\n"
                    f"Gunakan `/private_mine` untuk mulai menambang coin secara pribadi.\n"
                    f"Untuk menghapus channel ini, tekan tombol di bawah."
                ),
                color=discord.Color.blue()
            )
            view = DeletePrivateMineButton(str(channel.id), user_id, server_id)
            await channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"✅ Channel private mine {channel.mention} berhasil dibuat di category '{category_name}'! Cek channel untuk detailnya.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot tidak memiliki izin untuk membuat channel atau category.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error creating private mine channel: {str(e)}")
            await interaction.response.send_message("❌ Terjadi kesalahan. Coba lagi nanti.", ephemeral=True)

    @app_commands.command(name="hapus_private_mine", description="Hapus channel private mine milikmu")
    async def hapus_private_mine(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)

        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT channel_id FROM private_mine_channels WHERE user_id = %s AND server_id = %s", (user_id, server_id))
        channel_data = cur.fetchone()
        conn.close()

        if not channel_data:
            await interaction.response.send_message("❌ Kamu tidak memiliki channel private mine di server ini.", ephemeral=True)
            return

        try:
            channel = interaction.guild.get_channel(int(channel_data["channel_id"]))
            if channel:
                await channel.delete(reason=f"Private mine channel dihapus oleh {interaction.user.name}")
            if delete_private_mine_channel(channel_data["channel_id"]):
                await interaction.response.send_message("✅ Channel private mine berhasil dihapus.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Gagal menghapus data channel dari database.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot tidak memiliki izin untuk menghapus channel.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in hapus_private_mine: {str(e)}")
            await interaction.response.send_message("❌ Terjadi kesalahan. Coba lagi nanti.", ephemeral=True)
            
    @app_commands.command(name="coin_chart", description="Lihat grafik harga coin")
    async def coin_chart(self, interaction: discord.Interaction):
        image_path = generate_price_graph()
        if not image_path or not os.path.exists(image_path):
            await interaction.response.send_message("⚠️ Grafik belum tersedia.", ephemeral=True)
            return

        file = discord.File(image_path, filename="coin_graph.png")
        await interaction.response.send_message("📈 Grafik Harga Coin:", file=file)

    @app_commands.command(name="remaining_coin", description="Cek jumlah coin yang tersisa untuk bisa ditambang")
    async def remaining_coin(self, interaction: discord.Interaction):
        remaining = MAX_SUPPLY - get_total_mined()
        await interaction.response.send_message(f"🪙 Coin tersisa untuk ditambang: `{remaining:.2f}` dari total `{MAX_SUPPLY}`")

    @app_commands.command(name="balance", description="Lihat saldo coin kamu")
    async def balance(self, interaction: discord.Interaction):
        user = get_user_data(str(interaction.user.id))
        price = get_market_price()
        await interaction.response.send_message(
            f"💰 Saldo: `{user['balance']:.2f}` coin\n"
            f"🛒 Beli: `{user['bought']:.2f}` | 💸 Jual: `{user['sold']:.2f}`\n"
            f"🛠️ Rig: `{user['rig']}`\n"
            f"📈 Harga pasar: `{price:.2f}`"
        )

    @app_commands.command(name="mine_coin", description="Menambang coin 10x, 1x tiap 20 detik")
    async def mine_coin(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        user_name = interaction.user.name

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return

        self.mining_users.add(user_id)

        try:
            await interaction.response.defer()

            user = get_user_data(user_id)
            if not user:
                await interaction.followup.send("❌ Data pengguna tidak ditemukan. Coba lagi nanti.", ephemeral=True)
                return

            rig = user["rig"]

            rig_hardware = [
                    {
                        "cpu": "Intel Celeron",
                        "gpu": "GPU tidak terdeteksi",
                        "mainboard": "Basic Motherboard",
                        "ram": "4GB DDR3",
                        "ssd": "120GB SATA",
                        "psu": "300W Generic",
                        "power_usage": 50
                    },
                    {
                        "cpu": "Intel(R) Pentium G4400",
                        "gpu": "GPU tidak terdeteksi",
                        "mainboard": "H110M",
                        "ram": "8GB DDR4",
                        "ssd": "240GB SATA",
                        "psu": "350W Bronze",
                        "power_usage": 70
                    },
                    {
                        "cpu": "Intel(R) Core i3-8100",
                        "gpu": "NVIDIA GeForce GT 1030",
                        "mainboard": "B360M",
                        "ram": "16GB DDR4",
                        "ssd": "480GB SATA",
                        "psu": "400W Bronze",
                        "power_usage": 100
                    },
                    {
                        "cpu": "Intel(R) Core i5-8400",
                        "gpu": "NVIDIA GeForce GTX 1050 Ti",
                        "mainboard": "Z370",
                        "ram": "16GB DDR4",
                        "ssd": "500GB NVMe",
                        "psu": "450W Gold",
                        "power_usage": 150
                    },
                    {
                        "cpu": "Intel(R) Core i5-9600K",
                        "gpu": "NVIDIA GeForce GTX 1060",
                        "mainboard": "Z390",
                        "ram": "32GB DDR4",
                        "ssd": "1TB NVMe",
                        "psu": "500W Gold",
                        "power_usage": 200
                    },
                    {
                        "cpu": "Intel(R) Core i7-9700K",
                        "gpu": "NVIDIA GeForce GTX 1660 Ti",
                        "mainboard": "Z490",
                        "ram": "32GB DDR4",
                        "ssd": "1TB NVMe",
                        "psu": "550W Platinum",
                        "power_usage": 250
                    },
                    {
                        "cpu": "Intel(R) Core i7-10700",
                        "gpu": "NVIDIA GeForce RTX 2060",
                        "mainboard": "B560",
                        "ram": "64GB DDR4",
                        "ssd": "2TB NVMe",
                        "psu": "650W Platinum",
                        "power_usage": 300
                    },
                    {
                        "cpu": "AMD Ryzen 7 5800X",
                        "gpu": "NVIDIA GeForce RTX 3060 Ti",
                        "mainboard": "X570",
                        "ram": "64GB DDR4",
                        "ssd": "2TB NVMe",
                        "psu": "750W Titanium",
                        "power_usage": 350
                    },
                    {
                        "cpu": "Intel(R) Core i9-11900K",
                        "gpu": "NVIDIA GeForce RTX 3080 Ti",
                        "mainboard": "Z590",
                        "ram": "128GB DDR4",
                        "ssd": "4TB NVMe",
                        "psu": "850W Titanium",
                        "power_usage": 400
                    },
                    {
                        "cpu": "Intel(R) Core i9-11900K",
                        "gpu": "NVIDIA GeForce RTX 5090",
                        "mainboard": "Z690",
                        "ram": "128GB DDR5",
                        "ssd": "8TB NVMe",
                        "psu": "1000W Titanium",
                        "power_usage": 500
                    }
                ]
            hardware = rig_hardware[min(rig, len(rig_hardware)-1)]
            current_price = get_market_price()

            header = (
                f"👤 **User**: {user_name}\n"
                f"⚙️ **Jumlah Rig**: {rig}\n"
                f"💸 **Harga Coin**: {current_price:.4f}\n\n"
                f"**Spesifikasi Hardware**:\n"
                f"🧠 CPU: {hardware['cpu']}\n"
                f"🎮 GPU: {hardware['gpu']}\n"
                f"🔧 Mainboard: {hardware['mainboard']}\n"
                f"💾 RAM: {hardware['ram']}\n"
                f"💽 SSD: {hardware['ssd']}\n"
                f"🔋 PSU: {hardware['psu']}\n\n"
                f"**Proses Mining**:\n"
            )

            embed = discord.Embed(
                title="💻 Proses Mining Coin",
                description=header + "Mulai mining, tunggu hasil per ronde...",
                color=discord.Color.gold()
            )
            message = await interaction.followup.send(embed=embed)

            total_mined = 0
            total_power_usage = 0
            rewards = [0.2, 0.0] if rig > 0 else [0.01, 0.0]
            mining_results = []

            for i in range(10):
                await asyncio.sleep(5)

                cpu_percent = psutil.cpu_percent(interval=None)

                if cpu_percent >= 95.0:
                    mined = 0.01
                    cpu_note = f"⚠️ CPU tinggi ({cpu_percent:.1f}%), hasil otomatis: {mined:.3f}"
                else:
                    if rig > 0:
                        mined = round(sum([random.choice(rewards) for _ in range(rig)]), 3)
                        multiplier = 1 + (rig * 0.0)
                        mined = round(mined * multiplier, 3)
                    else:
                        mined = round(random.choice(rewards), 3)
                    cpu_note = f"🖥️ CPU: {cpu_percent:.1f}%"

                power_usage_watt = hardware["power_usage"]
                power_usage_kwh = (power_usage_watt * (20 / 3600)) / 1000
                total_power_usage += power_usage_kwh

                total_mined += mined
                symbol = "🟩" if mined > 0 else "🟥"
                mining_results.append(
                    f"`Ronde {i+1}/10` {symbol} Hasil: `{mined:.3f}` coin | {cpu_note} | 🔌 {power_usage_kwh:.5f} kWh"
                )

                embed.description = header + "\n".join(mining_results)
                await message.edit(embed=embed)

            embed.title = "✅ Mining Selesai"
            embed.description = (
                header.replace("**Proses Mining**", "**Hasil Mining**") +
                "\n".join(mining_results) +
                f"\n\n💰 **Total Coin**: `{total_mined:.3f}`\n"
                f"🔌 **Total Listrik**: {total_power_usage:.5f} kWh"
            )
            embed.color = discord.Color.green()
            await message.edit(embed=embed)

            current_mined = get_total_mined()
            if current_mined + total_mined > MAX_SUPPLY:
                total_mined = max(0, MAX_SUPPLY - current_mined)

            user["balance"] += total_mined
            update_user_data(user)
            set_total_mined(current_mined + total_mined)

        except Exception as e:
            await interaction.followup.send("❌ Terjadi kesalahan saat mining.", ephemeral=True)
        finally:
            self.mining_users.discard(user_id)

    @app_commands.command(name="buat_wallet_server", description="Buat wallet server pribadi di server ini")
    async def buat_wallet_server(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return

        wallet = get_user_server_wallet(user_id, server_id)
        if wallet:
            await interaction.response.send_message("❌ Kamu sudah memiliki wallet server di sini.", ephemeral=True)
            return

        wallet = create_user_server_wallet(user_id, server_id)
        if not wallet:
            await interaction.response.send_message("❌ Gagal membuat wallet server. Coba lagi nanti.", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Wallet Server Dibuat",
            description=(
                f"💰 Saldo awal: `0` coin\n"
                f"🛠️ Rig: `0`\n"
                f"📌 Wallet ini hanya untuk kamu di server ini."
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="add_rig_to_server", description="Tambahkan rig ke wallet server pribadimu di server ini")
    async def add_rig_to_server(self, interaction: discord.Interaction, jumlah: int):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        if jumlah <= 0:
            await interaction.response.send_message("❌ Jumlah rig harus lebih dari 0.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return

        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            conn.start_transaction()
            cur.execute("SELECT * FROM user_server_wallets WHERE user_id = %s AND server_id = %s FOR UPDATE", (user_id, server_id))
            wallet = cur.fetchone()
            if not wallet:
                await interaction.response.send_message("❌ Kamu belum memiliki wallet server. Buat dulu dengan `/buat_wallet_server`.", ephemeral=True)
                conn.rollback()
                return
            cur.execute("SELECT rig FROM users WHERE id = %s FOR UPDATE", (user_id,))
            user = cur.fetchone()
            if not user or user['rig'] < jumlah:
                await interaction.response.send_message("❌ Rig kamu tidak cukup.", ephemeral=True)
                conn.rollback()
                return
            cur.execute("UPDATE users SET rig = rig - %s WHERE id = %s", (jumlah, user_id))
            cur.execute("UPDATE user_server_wallets SET rig = rig + %s WHERE user_id = %s AND server_id = %s", (jumlah, user_id, server_id))
            cur.execute("SELECT rig FROM users WHERE id = %s", (user_id,))
            new_user_rig = cur.fetchone()['rig']
            cur.execute("SELECT rig FROM user_server_wallets WHERE user_id = %s AND server_id = %s", (user_id, server_id))
            new_server_rig = cur.fetchone()['rig']

            conn.commit()

            await interaction.response.send_message(
                f"✅ Kamu menambahkan `{jumlah}` rig ke wallet server pribadimu.\n"
                f"🛠️ Rig pribadi kamu: `{new_user_rig}`\n"
                f"🏢 Rig wallet server kamu: `{new_server_rig}`"
            )

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error in add_rig_to_server: {str(e)}")
            await interaction.response.send_message("❌ Terjadi kesalahan. Coba lagi nanti.", ephemeral=True)
        finally:
            if conn:
                conn.close()

    @app_commands.command(name="tarik_rig_dari_server", description="Tarik rig dari wallet server pribadimu ke inventaris pribadi")
    async def tarik_rig_dari_server(self, interaction: discord.Interaction, jumlah: int):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        if jumlah <= 0:
            await interaction.response.send_message("❌ Jumlah rig harus lebih dari 0.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return

        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            conn.start_transaction()
            cur.execute("SELECT * FROM user_server_wallets WHERE user_id = %s AND server_id = %s FOR UPDATE", (user_id, server_id))
            wallet = cur.fetchone()
            if not wallet:
                await interaction.response.send_message("❌ Kamu belum memiliki wallet server. Buat dulu dengan `/buat_wallet_server`.", ephemeral=True)
                conn.rollback()
                return
            if wallet['rig'] < jumlah:
                await interaction.response.send_message("❌ Rig di wallet server kamu tidak cukup.", ephemeral=True)
                conn.rollback()
                return
            cur.execute("SELECT rig FROM users WHERE id = %s FOR UPDATE", (user_id,))
            user = cur.fetchone()
            if not user:
                await interaction.response.send_message("❌ Data pengguna tidak ditemukan.", ephemeral=True)
                conn.rollback()
                return
            cur.execute("UPDATE user_server_wallets SET rig = rig - %s WHERE user_id = %s AND server_id = %s", (jumlah, user_id, server_id))
            cur.execute("UPDATE users SET rig = rig + %s WHERE id = %s", (jumlah, user_id))
            cur.execute("SELECT rig FROM users WHERE id = %s", (user_id,))
            new_user_rig = cur.fetchone()['rig']
            cur.execute("SELECT rig FROM user_server_wallets WHERE user_id = %s AND server_id = %s", (user_id, server_id))
            new_server_rig = cur.fetchone()['rig']

            conn.commit()

            embed = discord.Embed(
                title="✅ Rig Berhasil Ditarik",
                description=(
                    f"Kamu menarik `{jumlah}` rig dari wallet server pribadimu.\n"
                    f"🛠️ Rig pribadi kamu sekarang: `{new_user_rig}`\n"
                    f"🏢 Rig wallet server kamu sekarang: `{new_server_rig}`"
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error in tarik_rig_dari_server: {str(e)}")
            await interaction.response.send_message("❌ Terjadi kesalahan. Coba lagi nanti.", ephemeral=True)
        finally:
            if conn:
                conn.close()

    @app_commands.command(name="server_mine", description="Menambang coin untuk wallet server pribadimu di channel private mine (rig diperlukan)")
    async def server_mine(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)
        channel_id = str(interaction.channel_id)
        channel_data = get_private_mine_channel(channel_id)
        if not channel_data or (channel_data["user_id"] != user_id and not interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ Command ini hanya bisa digunakan di channel private mine milikmu atau oleh admin.",
                ephemeral=True
            )
            return

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return

        wallet = get_user_server_wallet(user_id, server_id)
        if not wallet:
            await interaction.response.send_message(
                "❌ Kamu belum memiliki wallet server. Buat dulu dengan `/buat_wallet_server`.",
                ephemeral=True
            )
            return

        rig = wallet["rig"]
        if rig <= 0:
            await interaction.response.send_message("🚫 Wallet server kamu belum memiliki rig untuk mining.", ephemeral=True)
            return

        self.mining_users.add(user_id)
        await interaction.response.defer()
        server_rig_hardware = [
            {
                "cpu": "Intel Xeon E-2388G",
                "gpu": "NVIDIA RTX 4060",
                "mainboard": "ASRock Rack W480",
                "ram": "32GB ECC DDR4",
                "ssd": "1TB NVMe Gen3",
                "psu": "650W Gold",
                "power_usage": 300
            },
            {
                "cpu": "Intel Xeon W-1370P",
                "gpu": "NVIDIA RTX 4070",
                "mainboard": "ASUS Pro WS W580-ACE",
                "ram": "64GB ECC DDR4",
                "ssd": "2TB NVMe Gen4",
                "psu": "800W Gold",
                "power_usage": 450
            },
            {
                "cpu": "AMD Ryzen Threadripper PRO 5955WX",
                "gpu": "NVIDIA RTX 4080",
                "mainboard": "ASUS WRX80 PRO WS SE",
                "ram": "128GB ECC DDR4",
                "ssd": "2x 2TB NVMe RAID",
                "psu": "1000W Platinum",
                "power_usage": 600
            },
            {
                "cpu": "AMD Threadripper PRO 5975WX",
                "gpu": "NVIDIA RTX 4090",
                "mainboard": "Gigabyte WRX80 SU8",
                "ram": "256GB ECC DDR4",
                "ssd": "4TB NVMe RAID",
                "psu": "1200W Platinum",
                "power_usage": 750
            },
            {
                "cpu": "Intel Xeon W9-3495X",
                "gpu": "2x NVIDIA RTX 4090",
                "mainboard": "ASUS W790E-SAGE SE",
                "ram": "512GB ECC DDR5",
                "ssd": "4x 4TB NVMe RAID10",
                "psu": "1600W Platinum",
                "power_usage": 900
            },
            {
                "cpu": "2x AMD EPYC 9654",
                "gpu": "2x NVIDIA RTX 6000 Ada",
                "mainboard": "Supermicro H13DSi",
                "ram": "768GB ECC DDR5",
                "ssd": "8TB Gen5 NVMe RAID",
                "psu": "1800W Platinum Redundant",
                "power_usage": 1100
            },
            {
                "cpu": "2x Intel Xeon Platinum 8490H",
                "gpu": "4x NVIDIA RTX 6000 Ada",
                "mainboard": "ASRock Rack C741D8U",
                "ram": "1TB ECC DDR5",
                "ssd": "16TB Gen5 NVMe RAID",
                "psu": "2000W Titanium",
                "power_usage": 1300
            },
            {
                "cpu": "4x AMD EPYC 9654",
                "gpu": "8x NVIDIA RTX 5000 Ada",
                "mainboard": "Custom SuperServer AI",
                "ram": "1.5TB ECC DDR5",
                "ssd": "32TB NVMe Gen5 RAID",
                "psu": "2500W Titanium",
                "power_usage": 1500
            },
            {
                "cpu": "4x AMD EPYC 9654",
                "gpu": "8x NVIDIA H100 SXM",
                "mainboard": "NVIDIA HGX Platform",
                "ram": "2TB ECC DDR5",
                "ssd": "64TB NVMe Gen5 RAID",
                "psu": "3000W Titanium Redundant",
                "power_usage": 1800
            },
            {
                "cpu": "8x AMD EPYC 9654",
                "gpu": "16x NVIDIA GH200 Grace Hopper",
                "mainboard": "DGX GH200 Platform",
                "ram": "4TB LPDDR5X Unified",
                "ssd": "128TB Gen5 NVMe AI Storage",
                "psu": "4000W Liquid-Cooled PSU",
                "power_usage": 2200
            }
        ]
        hardware = server_rig_hardware[min(len(server_rig_hardware) - 1, rig // 5)]
        current_price = get_market_price()

        header = (
            f"👤 **User**: {interaction.user.display_name}\n"
            f"⚙️ **Jumlah Rig (Server Wallet)**: {rig}\n"
            f"💸 **Harga Coin Saat Ini**: {current_price:.4f}\n\n"
            f"**Spesifikasi Hardware (Server Grade)**:\n"
            f"🧠 CPU: {hardware['cpu']}\n"
            f"🎮 GPU: {hardware['gpu']}\n"
            f"🔧 Mainboard: {hardware['mainboard']}\n"
            f"💾 RAM: {hardware['ram']}\n"
            f"💽 SSD: {hardware['ssd']}\n"
            f"🔋 PSU: {hardware['psu']}\n\n"
            f"**Proses Mining**:\n"
        )

        embed = discord.Embed(
            title="⛏️ Server Mining (Private Wallet)",
            description=header + "⏳ Mining dimulai, tunggu hasil setiap ronde...",
            color=discord.Color.dark_gold()
        )
        message = await interaction.followup.send(embed=embed)

        rewards = [0.04, 0.0]
        total_mined = 0
        total_power_usage = 0
        mining_results = []

        try:
            for i in range(25):
                await asyncio.sleep(10)

                mined = round(sum([random.choice(rewards) for _ in range(rig)]), 3)
                total_mined += mined

                power_kwh = (hardware['power_usage'] * (20 / 3600)) / 1000
                total_power_usage += power_kwh

                mining_results.append(
                    f"`Ronde {i+1}/25` 🟨 Mined: `{mined:.3f}` coin | 🔌 {power_kwh:.5f} kWh"
                )

                embed.description = header + "\n".join(mining_results)
                await message.edit(embed=embed)

            wallet["balance"] += total_mined
            update_user_server_wallet(user_id, server_id, balance=wallet["balance"])

            embed.title = "✅ Server Mining Selesai"
            embed.description = (
                header.replace("**Proses Mining**", "**Hasil Mining**") +
                "\n".join(mining_results) +
                f"\n\n💰 **Total Coin Diperoleh**: `{total_mined:.3f}`\n"
                f"🔌 **Total Konsumsi Listrik**: `{total_power_usage:.5f}` kWh"
            )
            embed.color = discord.Color.green()
            await message.edit(embed=embed)

        except Exception as e:
            logger.error(f"Error in server_mine for user {user_id}: {str(e)}")
            await interaction.followup.send("❌ Terjadi kesalahan saat mining.", ephemeral=True)
        finally:
            self.mining_users.discard(user_id)

    @app_commands.command(name="tarik_server_wallet", description="Menarik coin dari wallet server ke wallet utama")
    @app_commands.describe(jumlah="Jumlah coin yang ingin ditarik dari wallet server")
    async def tarik_server_coin(self, interaction: discord.Interaction, jumlah: float):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return
        
        if jumlah <= 0:
            await interaction.response.send_message("❌ Jumlah coin harus lebih dari 0.", ephemeral=True)
            return

        wallet_server = get_user_server_wallet(user_id, server_id)
        wallet_pribadi = get_user_data(user_id)

        if not wallet_server:
            await interaction.response.send_message("🚫 Kamu belum memiliki wallet server.", ephemeral=True)
            return

        if not wallet_pribadi:
            await interaction.response.send_message("🚫 Wallet utama tidak ditemukan.", ephemeral=True)
            return

        if wallet_server["balance"] < jumlah:
            await interaction.response.send_message(
                f"⚠️ Wallet server kamu hanya punya `{wallet_server['balance']:.3f}` coin.",
                ephemeral=True
            )
            return

        wallet_server["balance"] -= jumlah
        wallet_pribadi["balance"] += jumlah

        update_user_server_wallet(user_id, server_id, balance=wallet_server["balance"])
        update_user_data(wallet_pribadi)

        await interaction.response.send_message(
            f"✅ Berhasil menarik `{jumlah:.3f}` coin dari wallet server ke wallet utama kamu.\n"
            f"💰 Sisa Wallet Server: `{wallet_server['balance']:.3f}`\n"
            f"💼 Wallet Pribadi Sekarang: `{wallet_pribadi['balance']:.3f}`",
            ephemeral=True
        )

    @app_commands.command(name="wallet_server", description="Lihat wallet server pribadimu di server ini")
    async def wallet_server(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)

        wallet = get_user_server_wallet(user_id, server_id)
        if not wallet:
            await interaction.response.send_message("❌ Kamu belum memiliki wallet server. Buat dulu dengan `/buat_wallet_server`.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🏢 Wallet Server Pribadimu",
            description=(
                f"💰 Saldo: `{wallet['balance']:.3f}` coin\n"
                f"🛠️ Rig: `{wallet['rig']}`\n"
                f"📅 Dibuat: <t:{int(wallet['created_at'].timestamp())}:R>\n\n"
                f"📌 Ini adalah wallet server pribadimu di server ini."
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="give_coin", description="Transfer coin ke user lain")
    async def give_coin(self, interaction: discord.Interaction, member: discord.Member, amount: float):
        if amount <= 0:
            await interaction.response.send_message("❌ Jumlah harus lebih dari 0.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return

        sender_id = str(interaction.user.id)
        receiver_id = str(member.id)
        if sender_id == receiver_id:
            await interaction.response.send_message("❌ Tidak bisa mengirim ke diri sendiri.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=False)

        sender = get_user_data(sender_id)
        receiver = get_user_data(receiver_id)

        if sender["balance"] < amount:
            await interaction.followup.send("❌ Coin kamu tidak cukup.", ephemeral=True)
            return

        sender["balance"] -= amount
        sender["sold"] += amount
        receiver["balance"] += amount
        receiver["bought"] += amount

        update_user_data(sender)
        update_user_data(receiver)

        await interaction.followup.send(f"✅ Kamu mengirim `{amount:.2f}` coin ke {member.mention}.")

    @app_commands.command(name="buy_rig", description="Beli rig untuk menambang coin")
    async def buy_rig(self, interaction: discord.Interaction, jumlah: int = 1):
        user_id = str(interaction.user.id)
        user = get_user_data(user_id)

        harga = 5000 * jumlah
        if user["balance"] < harga:
            await interaction.response.send_message(f"❌ Coin kamu tidak cukup untuk beli `{jumlah}` rig seharga `{harga}`.", ephemeral=True)
            return

        user["balance"] -= harga
        user["rig"] += jumlah
        update_user_data(user)

        await interaction.response.send_message(f"🛠️ Kamu membeli `{jumlah}` rig. Total rig sekarang: `{user['rig']}`")

    @app_commands.command(name="give_rig", description="Berikan rig ke user (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def give_rig(self, interaction: discord.Interaction, member: discord.Member, jumlah: int):
        user_id = str(interaction.user.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return
        
        user = get_user_data(str(member.id))
        user["rig"] += jumlah
        update_user_data(user)
        await interaction.response.send_message(f"✅ {member.mention} diberi `{jumlah}` rig. Total sekarang: `{user['rig']}`")

    from datetime import datetime, timedelta

    @app_commands.command(name="claim_income", description="Klaim income harian berdasarkan jumlah rig")
    async def claim_income(self, interaction: Interaction):
        user_id = str(interaction.user.id)
        user = get_user_data(user_id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return

        now = datetime.datetime.utcnow()
        last_claim = user.get("last_claim")

        if last_claim:
            if isinstance(last_claim, str):
                last_claim = datetime.fromisoformat(last_claim)
            cooldown = timedelta(hours=24)
            if now - last_claim < cooldown:
                next_claim = last_claim + cooldown
                sisa = next_claim - now
                jam, menit = divmod(sisa.seconds // 60, 60)
                return await interaction.response.send_message(
                    f"⏳ Kamu sudah klaim. Klaim lagi dalam {sisa.days} hari {jam} jam {menit} menit.",
                    ephemeral=True
                )

        rig = user["rig"]
        if rig <= 0:
            return await interaction.response.send_message("🚫 Kamu belum punya rig untuk klaim income.", ephemeral=True)

        income_per_rig = random.uniform(0.1, 0.5)
        total_income = round(rig * income_per_rig, 3)

        user["balance"] += total_income
        user["last_claim"] = now.isoformat()
        update_user_data(user)

        await interaction.response.send_message(
            f"✅ Kamu klaim income sebesar `{total_income:.3f}` coin berdasarkan `{rig}` rig yang kamu miliki.\n"
            f"📈 Setiap rig menghasilkan `{income_per_rig:.3f}` coin kali ini."
        )
        
    @app_commands.command(name="leaderboard_coin", description="Lihat leaderboard top 10 coin")
    async def leaderboard_coin(self, interaction: discord.Interaction):
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users ORDER BY balance DESC LIMIT 10")
        rows = cur.fetchall()
        conn.close()

        embed = discord.Embed(title="🏆 Coin Leaderboard (Top 10)", color=discord.Color.blurple())
        for i, user in enumerate(rows, start=1):
            uid = int(user["id"])
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else f"User {uid}"
            embed.add_field(
                name=f"#{i} {name}",
                value=f"💰 `{user['balance']:.2f}` coin | 🛠️ `{user['rig']}` rig",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buat_wallet", description="Buat private wallet baru dengan password unik")
    async def buat_wallet(self, interaction: discord.Interaction):
        """Membuat wallet pribadi baru"""
        user_id = str(interaction.user.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return
        
        existing_wallets = get_user_wallets(user_id)
        if existing_wallets:
            await interaction.response.send_message(
                "⚠️ Kamu sudah memiliki private wallet. Gunakan `/wallet_saya` untuk melihat daftar wallet kamu.",
                ephemeral=True
            )
            return
        
        wallet = create_private_wallet(user_id)
        if not wallet:
            await interaction.response.send_message(
                "❌ Gagal membuat wallet. Kamu mungkin sudah memiliki wallet.",
                ephemeral=True
            )
            return
        
        try:
            await interaction.user.send(
                f"🔐 **Private Wallet Baru Berhasil Dibuat**\n\n"
                f"📌 Password wallet: `{wallet['password']}`\n"
                f"💰 Saldo awal: `0` coin\n\n"
                f"⚠️ **Simpan password ini baik-baik!** Siapa pun yang mengetahui password ini bisa mengakses wallet ini!"
            )
            await interaction.response.send_message(
                "✅ Wallet berhasil dibuat! Cek DM kamu untuk mendapatkan password.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Tidak bisa mengirim DM ke kamu. Pastikan DM kamu terbuka untuk menerima pesan dari bot.",
                ephemeral=True
            )

    @app_commands.command(name="wallet_saya", description="Lihat daftar private wallet milikmu")
    async def wallet_saya(self, interaction: discord.Interaction):
        """Menampilkan semua wallet milik user"""
        user_id = str(interaction.user.id)
        wallets = get_user_wallets(user_id)
        
        if not wallets:
            await interaction.response.send_message(
                "❌ Kamu belum memiliki private wallet. Buat dulu dengan `/buat_wallet`.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"🔐 Private Wallet Milik {interaction.user.display_name}",
            color=discord.Color.blue()
        )
        
        for wallet in wallets:
            embed.add_field(
                name=f"Wallet `{wallet['password'][:4]}...`",
                value=f"💰 Saldo: `{wallet['balance']:.2f}` coin",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="isi_wallet", description="Isi saldo private wallet dari balance utama")
    async def isi_wallet(self, interaction: discord.Interaction, password: str, amount: float):
        """Mengisi saldo wallet dari balance utama"""
        if amount <= 0:
            await interaction.response.send_message("❌ Jumlah harus lebih dari 0.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        user_data = get_user_data(user_id)
        if user_data['balance'] < amount:
            await interaction.response.send_message("❌ Saldo utama kamu tidak cukup.", ephemeral=True)
            return
        wallet = get_private_wallet(password)
        if not wallet or wallet['user_id'] != user_id:
            await interaction.response.send_message("❌ Password wallet tidak valid atau wallet bukan milik kamu.", ephemeral=True)
            return
        conn = get_connection()
        cur = conn.cursor()
        
        try:
            user_data['balance'] -= amount
            update_user_data(user_data)
            new_balance = wallet['balance'] + amount
            update_wallet_balance(password, new_balance)
            
            conn.commit()
            await interaction.response.send_message(
                f"✅ Berhasil mengisi wallet sebesar `{amount:.2f}` coin.\n"
                f"💰 Saldo wallet sekarang: `{new_balance:.2f}` coin",
                ephemeral=True
            )
        except Exception as e:
            conn.rollback()
            await interaction.response.send_message(
                "❌ Gagal melakukan transfer. Silakan coba lagi.",
                ephemeral=True
            )
        finally:
            conn.close()

    @app_commands.command(name="transfer_from_wallet", description="Transfer coin dari private wallet ke user lain")
    async def transfer_from_wallet(self, interaction: discord.Interaction, password: str, member: discord.Member, amount: float):
        """Transfer coin dari private wallet ke user lain"""
        if amount <= 0:
            await interaction.response.send_message("❌ Jumlah harus lebih dari 0.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return
        
        sender_id = str(interaction.user.id)
        receiver_id = str(member.id)
        
        if sender_id == receiver_id:
            await interaction.response.send_message("❌ Tidak bisa transfer ke diri sendiri.", ephemeral=True)
            return
        
        wallet = get_private_wallet(password)
        if not wallet or wallet['user_id'] != sender_id:
            await interaction.response.send_message("❌ Password wallet tidak valid atau wallet bukan milik kamu.", ephemeral=True)
            return
        if wallet['balance'] < amount:
            await interaction.response.send_message("❌ Saldo wallet tidak cukup.", ephemeral=True)
            return
        
        receiver_data = get_user_data(receiver_id)
        
        conn = get_connection()
        cur = conn.cursor()
        
        try:
            new_sender_balance = wallet['balance'] - amount
            update_wallet_balance(password, new_sender_balance)
            
            receiver_data['balance'] += amount
            receiver_data['bought'] += amount
            update_user_data(receiver_data)
            
            price = get_market_price()
            price -= random.uniform(0.001, 0.005) * amount
            set_market_price(max(0.1, round(price, 4)))
            append_price_history(price)
            
            conn.commit()
            
            embed = discord.Embed(
                title="✅ Transfer Berhasil",
                description=(
                    f"📤 Pengirim: {interaction.user.mention}\n"
                    f"📥 Penerima: {member.mention}\n"
                    f"💰 Jumlah: `{amount:.2f}` coin\n"
                    f"🔐 Sisa saldo wallet: `{new_sender_balance:.2f}` coin"
                ),
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed)
            try:
                await member.send(
                    f"💸 Kamu menerima transfer `{amount:.2f}` coin dari {interaction.user.name}.\n"
                    f"Saldo kamu sekarang: `{receiver_data['balance']:.2f}` coin"
                )
            except discord.Forbidden:
                pass
                
        except Exception as e:
            conn.rollback()
            await interaction.response.send_message(
                "❌ Gagal melakukan transfer. Silakan coba lagi.",
                ephemeral=True
            )
        finally:
            conn.close()

    @app_commands.command(name="cek_wallet", description="Cek saldo private wallet dengan password")
    async def cek_wallet(self, interaction: discord.Interaction, password: str):
        """Mengecek saldo wallet dengan password"""
        wallet = get_private_wallet(password)
        if not wallet:
            await interaction.response.send_message("❌ Wallet tidak ditemukan. Password salah.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔐 Private Wallet Info",
            description=(
                f"💰 Saldo: `{wallet['balance']:.2f}` coin\n"
                f"📅 Dibuat oleh: <@{wallet['user_id']}>"
            ),
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="tarik_private_wallet", description="Tarik coin dari private wallet ke balance utama")
    async def tarik_dari_wallet(self, interaction: discord.Interaction, password: str, amount: float):
        """Menarik coin dari wallet ke balance utama"""
        if amount <= 0:
            await interaction.response.send_message("❌ Jumlah harus lebih dari 0.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)

        if user_id in self.mining_users:
            await interaction.response.send_message("⚠️ Kamu sedang dalam proses mining. Harap tunggu hingga selesai.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        wallet = get_private_wallet(password)
        if not wallet or wallet['user_id'] != user_id:
            await interaction.response.send_message("❌ Password wallet tidak valid atau wallet bukan milik kamu.", ephemeral=True)
            return
        if wallet['balance'] < amount:
            await interaction.response.send_message("❌ Saldo wallet tidak cukup.", ephemeral=True)
            return
        conn = get_connection()
        cur = conn.cursor()
        
        try:
            new_wallet_balance = wallet['balance'] - amount
            update_wallet_balance(password, new_wallet_balance)
            
            user_data = get_user_data(user_id)
            user_data['balance'] += amount
            update_user_data(user_data)
            
            conn.commit()
            
            await interaction.response.send_message(
                f"✅ Berhasil menarik `{amount:.2f}` coin dari wallet.\n"
                f"💰 Saldo wallet sekarang: `{new_wallet_balance:.2f}` coin\n"
                f"💵 Saldo utama sekarang: `{user_data['balance']:.2f}` coin",
                ephemeral=True
            )
        except Exception as e:
            conn.rollback()
            await interaction.response.send_message(
                "❌ Gagal melakukan penarikan. Silakan coba lagi.",
                ephemeral=True
            )
        finally:
            conn.close()

class MyBot(commands.Bot):
    async def setup_hook(self):
        init_database()
        await self.load_extension("cogs.coin_system")

async def setup(bot):
    await bot.add_cog(CoinSystem(bot))