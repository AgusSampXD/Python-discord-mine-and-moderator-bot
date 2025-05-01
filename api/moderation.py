import discord
from discord.ext import commands
from discord import app_commands
import json, os

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/mod_role.json"
        self.seller_path = "data/seller_role.json"

        for path in [self.config_path, self.seller_path]:
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump({}, f)

    def get_allowed_role(self, guild_id):
        with open(self.config_path, "r") as f:
            config = json.load(f)
        return config.get(str(guild_id))

    def set_allowed_role(self, guild_id, role_id):
        with open(self.config_path, "r") as f:
            config = json.load(f)
        config[str(guild_id)] = role_id
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    def get_seller_role(self, guild_id):
        with open(self.seller_path, "r") as f:
            config = json.load(f)
        return config.get(str(guild_id))

    def set_seller_role(self, guild_id, role_id):
        with open(self.seller_path, "r") as f:
            config = json.load(f)
        config[str(guild_id)] = role_id
        with open(self.seller_path, "w") as f:
            json.dump(config, f, indent=4)

    def is_allowed():
        async def predicate(interaction: discord.Interaction):
            cog = interaction.client.get_cog("Moderation")
            role_id = cog.get_allowed_role(interaction.guild.id)
            if role_id:
                role = discord.utils.get(interaction.user.roles, id=role_id)
                if role:
                    return True
            await interaction.response.send_message("🚫 Perintah ini hanya bisa digunakan oleh role yang diizinkan.", ephemeral=True)
            return False
        return app_commands.check(predicate)

    def is_seller():
        async def predicate(interaction: discord.Interaction):
            cog = interaction.client.get_cog("Moderation")
            role_id = cog.get_seller_role(interaction.guild.id)
            if role_id:
                role = discord.utils.get(interaction.user.roles, id=role_id)
                if role:
                    return True
            await interaction.response.send_message("🚫 Perintah ini hanya bisa digunakan oleh seller yang diizinkan.", ephemeral=True)
            return False
        return app_commands.check(predicate)

    @app_commands.command(name="setmodrole", description="Set role yang diizinkan menggunakan perintah moderator")
    async def setmodrole(self, interaction: discord.Interaction, role: discord.Role):
        self.set_allowed_role(interaction.guild.id, role.id)
        await interaction.response.send_message(f"✅ Role moderator diset ke **{role.name}**")
    
    @app_commands.command(name="setseller", description="Set role yang diizinkan menggunakan perintah keuangan")
    async def setseller(self, interaction: discord.Interaction, role: discord.Role):
        self.set_seller_role(interaction.guild.id, role.id)
        await interaction.response.send_message(f"✅ Role seller diset ke **{role.name}**")
    ### AGUSSAMP/SITSU STUDIO
    @app_commands.command(name="kick", description="Kick member dari server")
    @is_allowed()
    async def kick(self, interaction: discord.Interaction, member: discord.Member, alasan: str = "Tidak ada alasan"):
        await member.kick(reason=alasan)
        await interaction.response.send_message(f"✅ {member.mention} telah di-kick. Alasan: {alasan}")

    @app_commands.command(name="add_role", description="Menambahkan role ke member")
    @is_allowed()
    async def add_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await member.add_roles(role)
        await interaction.response.send_message(f"✅ {role.name} ditambahkan ke {member.mention}")

    @app_commands.command(name="remove_role", description="Menghapus role dari member")
    @is_allowed()
    async def remove_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await member.remove_roles(role)
        await interaction.response.send_message(f"✅ {role.name} dihapus dari {member.mention}")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
