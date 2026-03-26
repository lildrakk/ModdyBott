import discord

from discord.ext import commands

from discord import app_commands

import json, os, aiohttp, io

WELCOME_FILE = "welcome.json"

# ============================

# JSON

# ============================

def load_welcome():

    if not os.path.exists(WELCOME_FILE):

        with open(WELCOME_FILE, "w") as f:

            json.dump({}, f, indent=4)

    with open(WELCOME_FILE, "r") as f:

        return json.load(f)

def save_welcome(data):

    with open(WELCOME_FILE, "w") as f:

        json.dump(data, f, indent=4)

# ============================

# COG PRINCIPAL

# ============================

class WelcomeCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # ============================

    # /welcome (todo en uno)

    # ============================

    @app_commands.command(

        name="welcome",

        description="Configura la bienvenida del servidor."

    )

    @app_commands.describe(

        estado="Activar o desactivar la bienvenida",

        canal="Canal donde se enviará la bienvenida",

        mensaje="Mensaje personalizado (usa {user}, {server}, {membercount})",

        imagen_url="URL de la imagen",

        imagen_archivo="Adjunta una imagen"

    )

    @app_commands.choices(

        estado=[

            app_commands.Choice(name="Activar", value="activar"),

            app_commands.Choice(name="Desactivar", value="desactivar")

        ]

    )

    async def welcome(

        self,

        interaction: discord.Interaction,

        estado: app_commands.Choice[str],

        canal: discord.TextChannel = None,

        mensaje: str = None,

        imagen_url: str = None,

        imagen_archivo: discord.Attachment = None

    ):

        data = load_welcome()

        gid = str(interaction.guild.id)

        # Crear config si no existe

        if gid not in data:

            data[gid] = {

                "enabled": False,

                "canal": None,

                "mensaje": "Bienvenido {user} a {server}!",

                "imagen": None

            }

        cfg = data[gid]

        # Cambiar estado

        cfg["enabled"] = (estado.value == "activar")

        # Cambiar canal

        if canal:

            cfg["canal"] = canal.id

        # Cambiar mensaje

        if mensaje:

            cfg["mensaje"] = mensaje

        # Imagen por archivo

        if imagen_archivo:

            cfg["imagen"] = imagen_archivo.url

        # Imagen por URL

        elif imagen_url:

            cfg["imagen"] = imagen_url

        save_welcome(data)

        await interaction.response.send_message(

            "✔ Configuración de bienvenida actualizada.",

            ephemeral=True

        )

    # ============================

    # EVENTO REAL

    # ============================

    @commands.Cog.listener()

    async def on_member_join(self, member: discord.Member):

        data = load_welcome()

        gid = str(member.guild.id)

        if gid not in data:

            return

        cfg = data[gid]

        if not cfg["enabled"] or not cfg["canal"]:

            return

        canal = member.guild.get_channel(cfg["canal"])

        if not canal:

            return

        mensaje = cfg["mensaje"]

        mensaje = mensaje.replace("{user}", member.mention)

        mensaje = mensaje.replace("{server}", member.guild.name)

        mensaje = mensaje.replace("{membercount}", str(member.guild.member_count))

        # Imagen opcional

        if cfg["imagen"]:

            try:

                async with aiohttp.ClientSession() as session:

                    async with session.get(cfg["imagen"]) as resp:

                        img = await resp.read()

                        file = discord.File(io.BytesIO(img), filename="welcome.png")

                        await canal.send(mensaje, file=file)

            except:

                await canal.send(mensaje)

        else:

            await canal.send(mensaje)

# ============================

# SETUP

# ============================

async def setup(bot):

    await bot.add_cog(WelcomeCog(bot))