import discord
from discord.ext import commands
import asyncio
import random
import datetime
import json
import os

RUTA_JSON = "giveaways.json"

# ============================
# CARGAR / GUARDAR JSON
# ============================

def cargar_giveaways():
    if not os.path.exists(RUTA_JSON):
        with open(RUTA_JSON, "w") as f:
            json.dump({}, f)
    with open(RUTA_JSON, "r") as f:
        return json.load(f)

def guardar_giveaways(data):
    with open(RUTA_JSON, "w") as f:
        json.dump(data, f, indent=4)

giveaways = cargar_giveaways()

# ============================
# VIEW DEL BOTÓN DE PARTICIPAR
# ============================

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = str(giveaway_id)

    @discord.ui.button(label="🎉 Participar", style=discord.ButtonStyle.blurple)
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = giveaways.get(self.giveaway_id)

        if not data:
            return await interaction.response.send_message(
                "❌ Este sorteo ya no existe.",
                ephemeral=True
            )

        user = interaction.user

        if str(user.id) in data["participantes"]:
            return await interaction.response.send_message(
                "❗ Ya estabas participando en este sorteo.",
                ephemeral=True
            )

        data["participantes"].append(str(user.id))
        guardar_giveaways(giveaways)

        await interaction.response.send_message(
            "🎉 ¡Has entrado correctamente al sorteo!",
            ephemeral=True
        )

# ============================
# COG PRINCIPAL
# ============================

class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # /giveaway
    # ============================

    @discord.app_commands.command(
        name="giveaway",
        description="Crea un sorteo (10s, 5m, 2h, 1d)."
    )
    @discord.app_commands.describe(
        tiempo="Duración del sorteo (10s, 5m, 2h, 1d)",
        ganadores="Cantidad de ganadores",
        premio="Premio del sorteo",
        gif="Enlace del GIF para mostrar en el embed"
    )
    async def giveaway(self, interaction: discord.Interaction, tiempo: str, ganadores: int, premio: str, gif: str):

        unidades = {"s":1, "m":60, "h":3600, "d":86400}

        if tiempo[-1].lower() not in unidades:
            return await interaction.response.send_message(
                "❌ Formato inválido. Usa: 10s, 5m, 2h, 1d",
                ephemeral=True
            )

        try:
            cantidad = int(tiempo[:-1])
        except:
            return await interaction.response.send_message(
                "❌ El tiempo debe empezar con un número. Ejemplo: 10s",
                ephemeral=True
            )

        duracion = cantidad * unidades[tiempo[-1].lower()]
        fin = datetime.datetime.utcnow() + datetime.timedelta(seconds=duracion)

        giveaway_id = random.randint(100000, 999999)

        giveaways[str(giveaway_id)] = {
            "host": interaction.user.id,
            "premio": premio,
            "fin": int(fin.timestamp()),
            "participantes": [],
            "canal": interaction.channel.id,
            "ganadores": ganadores
        }

        guardar_giveaways(giveaways)

        # ============================
        # EMBED ESTILO BLUECAT PERO ORIGINAL
        # ============================

        embed = discord.Embed(
            title="🎁 **SORTEO ACTIVO**",
            description=(
                "🎉 ¡Un nuevo sorteo ha comenzado en el servidor!\n\n"
                "**Cómo participar:**\n"
                "➡️ Pulsa el botón **Participar** de abajo\n"
                "➡️ Permanece en el servidor durante todo el sorteo\n"
                "➡️ Espera a que finalice el tiempo\n\n"
                "📌 *Si intentas unirte dos veces, el bot te avisará.*"
            ),
            color=discord.Color(0x0A3D62)
        )

        embed.add_field(name="🏆 Premio", value=premio, inline=False)
        embed.add_field(name="🥇 Ganadores", value=str(ganadores), inline=True)
        embed.add_field(name="👤 Organizado por", value=interaction.user.mention, inline=True)
        embed.add_field(name="⏳ Finaliza", value=f"<t:{int(fin.timestamp())}:R>", inline=False)

        embed.set_footer(text=f"ID del sorteo: {giveaway_id}")

        # GIF SOLO EN EL EMBED DEL GIVEAWAY
        embed.set_image(url=gif)

        view = GiveawayView(giveaway_id)

        await interaction.response.send_message(embed=embed, view=view)

        # Esperar a que termine
        await asyncio.sleep(duracion)

        data = giveaways.get(str(giveaway_id))
        if not data:
            return

        participantes = data["participantes"]

        if len(participantes) == 0:
            await interaction.channel.send(f"❌ Nadie participó en el sorteo **{giveaway_id}**.")
            del giveaways[str(giveaway_id)]
            guardar_giveaways(giveaways)
            return

        ganadores_finales = random.sample(
            participantes,
            min(len(participantes), data["ganadores"])
        )

        resultado = discord.Embed(
            title="🎉 **SORTEO FINALIZADO**",
            description="¡Aquí están los ganadores!",
            color=discord.Color(0x0A3D62)
        )

        resultado.add_field(name="🏆 Premio", value=data["premio"], inline=False)
        resultado.add_field(
            name="🥇 Ganadores",
            value="\n".join([f"<@{g}>" for g in ganadores_finales]),
            inline=False
        )

        resultado.set_footer(text=f"ID del sorteo: {giveaway_id}")

        await interaction.channel.send(embed=resultado)

    # ============================
    # /reroll
    # ============================

    @discord.app_commands.command(
        name="reroll",
        description="Elige nuevos ganadores usando el ID del sorteo."
    )
    @discord.app_commands.describe(
        giveaway_id="ID del sorteo (lo ves en el embed)"
    )
    async def reroll(self, interaction: discord.Interaction, giveaway_id: int):

        data = giveaways.get(str(giveaway_id))

        if not data:
            return await interaction.response.send_message(
                "❌ Ese ID de sorteo no existe.",
                ephemeral=True
            )

        if interaction.user.id != data["host"]:
            return await interaction.response.send_message(
                "❌ Solo el creador del sorteo puede hacer reroll.",
                ephemeral=True
            )

        participantes = data["participantes"]

        if len(participantes) == 0:
            return await interaction.response.send_message(
                "❌ No hay participantes para reroll.",
                ephemeral=True
            )

        ganadores_finales = random.sample(
            participantes,
            min(len(participantes), data["ganadores"])
        )

        embed = discord.Embed(
            title="🔄 **REROLL REALIZADO**",
            description="Se han elegido nuevos ganadores",
            color=discord.Color(0x0A3D62)
        )

        embed.add_field(name="🏆 Premio", value=data["premio"], inline=False)
        embed.add_field(
            name="🥇 Nuevos ganadores",
            value="\n".join([f"<@{g}>" for g in ganadores_finales]),
            inline=False
        )

        embed.set_footer(text=f"ID del sorteo: {giveaway_id}")

        await interaction.response.send_message(embed=embed)

# ============================
# SETUP
# ============================

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
