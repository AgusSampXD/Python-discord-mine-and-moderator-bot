import discord
from discord.ext import commands
from discord import app_commands
import json, os

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/welcome_config.json"
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                json.dump({}, f)

    def load_config(self, guild_id):
        with open(self.config_path, "r") as f:
            config = json.load(f)
        return config.get(str(guild_id), {})

    def save_config(self, guild_id, data):
        with open(self.config_path, "r") as f:
            config = json.load(f)
        config[str(guild_id)] = data
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = self.load_config(member.guild.id)
        role_name = config.get("role")
        channel_id = config.get("channel")

        if role_name:
            role = discord.utils.get(member.guild.roles, name=role_name)
            if role:
                await member.add_roles(role)

        if channel_id:
            channel = member.guild.get_channel(channel_id)
            if channel:
                await channel.send(f"🎉 Selamat datang {member.mention} di server {member.guild.name}!")

    @app_commands.command(name="setwelcome", description="Set channel welcome dan role otomatis untuk member baru")
    @app_commands.describe(channel="Channel tujuan welcome", role="Role otomatis untuk member baru")
    async def setwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        self.save_config(interaction.guild.id, {"channel": channel.id, "role": role.name})
        await interaction.response.send_message(f"✅ Channel welcome diset ke {channel.mention} dan role ke **{role.name}**")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
