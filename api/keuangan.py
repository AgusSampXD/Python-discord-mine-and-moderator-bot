import discord
from discord.ext import commands
from discord import app_commands
import json, os
import matplotlib.pyplot as plt
import io

class Keuangan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_data(self):
        with open("data/transaksi.json", "r") as f:
            content = f.read().strip()
            if not content:
                return {"produk": {}, "pendapatan": 0, "pengeluaran": 0}
            return json.loads(content)

    def save_data(self, data):
        with open("data/transaksi.json", "w") as f:
            json.dump(data, f, indent=4)

    def is_seller():
        async def predicate(interaction: discord.Interaction):
            cog = interaction.client.get_cog("Moderation")
            if not cog:
                await interaction.response.send_message("⚠️ Sistem Moderation belum aktif.", ephemeral=True)
                return False
            role_id = cog.get_seller_role(interaction.guild.id)
            if role_id:
                role = discord.utils.get(interaction.user.roles, id=role_id)
                if role:
                    return True
            await interaction.response.send_message("🚫 Perintah ini hanya bisa digunakan oleh seller yang diizinkan.", ephemeral=True)
            return False
        return app_commands.check(predicate)

    @app_commands.command(name="catat_transaksi", description="Catat penjualan produk")
    @is_seller()
    async def catat_transaksi(self, interaction: discord.Interaction, nama_produk: str, jumlah: int, harga: int):
        data = self.load_data()
        data['produk'][nama_produk] = data['produk'].get(nama_produk, 0) + jumlah
        data['pendapatan'] += jumlah * harga
        self.save_data(data)
        await interaction.response.send_message(f"Transaksi dicatat: {jumlah}x {nama_produk} = {jumlah * harga}")

    @app_commands.command(name="catat_pengeluaran", description="Catat pengeluaran dana")
    @is_seller()
    async def catat_pengeluaran(self, interaction: discord.Interaction, keterangan: str, jumlah: int):
        data = self.load_data()
        ### AGUSSAMP/SITSU STUDIO
        data['pengeluaran'] += jumlah
        self.save_data(data)
        await interaction.response.send_message(f"Pengeluaran dicatat: {keterangan} sebesar {jumlah}")

    @app_commands.command(name="grafik_pie", description="Lihat grafik bundar produk terjual")
    @is_seller()
    async def grafik_pie(self, interaction: discord.Interaction):
        data = self.load_data()
        produk = data['produk']
        if not produk:
            await interaction.response.send_message("Belum ada data produk.")
            return
        labels = list(produk.keys())
        sizes = list(produk.values())
        plt.figure(figsize=(6, 6))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.title("Persentase Produk Terjual")
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        plt.close()
        file = discord.File(fp=buffer, filename="grafik_pie.png")
        await interaction.response.send_message(file=file)

    @app_commands.command(name="testimoni", description="Tambahkan testimoni customer")
    async def testimoni(self, interaction: discord.Interaction, user: discord.User, pesan: str):
        try:
            os.makedirs("data", exist_ok=True)

            testimoni_path = "data/testimoni.json"
            if not os.path.exists(testimoni_path):
                with open(testimoni_path, "w") as f:
                    json.dump([], f)

            with open(testimoni_path, "r") as f:
                content = f.read().strip()
                data = json.loads(content) if content else []

            data.append({"user": user.name, "pesan": pesan})
            with open(testimoni_path, "w") as f:
                json.dump(data, f, indent=4)

            await interaction.response.send_message("✅ Testimoni dicatat!", ephemeral=True)

            channel = discord.utils.get(interaction.guild.text_channels, name="testimoni")
            if channel:
                await channel.send(f"📢 **{user.name}** bilang: {pesan}")

        except Exception as e:
            await interaction.response.send_message(f"❌ Gagal menyimpan testimoni.\nError: `{e}`", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Keuangan(bot))
