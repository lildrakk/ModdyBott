import discord

from discord.ext import commands

from discord import app_commands

import json

import os

import random

import string

from PIL import Image, ImageDraw, ImageFont

import io

import time

import datetime

VERIFICATION_FILE = os.path.join(os.path.dirname(__file__), "..", "verification.json")

# ============================

# JSON

# ============================

def save_verification(data):

    with open(VERIFICATION_FILE, "w") as f:

        json.dump(data, f, indent=4)

def load_verification():

    if not os.path.exists(VERIFICATION_FILE):

        save_verification({})

        return {}

    try:

        with open(VERIFICATION_FILE, "r") as f:

            data = json.load(f)

            if not isinstance(data, dict):

                save_verification({})

                return {}

            return data

    except:

        save_verification({})

        return {}

def sanitize_panel_id(panel_id: str) -> str:

    return panel_id.strip().replace(" ", "_")

def is_valid_panel_id(panel_id: str) -> bool:

    panel_id = panel_id.strip()

    if not panel_id:

        return False

    allowed = string.ascii_letters + string.digits + "_-"

    return all(c in allowed for c in panel_id)

# ============================

# NUEVO CAPTCHA (MEJORADO)

# ============================

def generar_captcha():

    letras = string.ascii_uppercase + string.digits

    codigo = ''.join(random.choice(letras) for _ in range(6))

    width, height = 500, 200

    img = Image.new("RGB", (width, height), (0, 0, 0))

    draw = ImageDraw.Draw(img)

    # Fondo degradado

    for y in range(height):

        r = int(40 + (y / height) * 40)

        g = int(20 + (y / height) * 60)

        b = int(80 + (y / height) * 100)

        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Líneas diagonales estilo circuito

    for i in range(0, width, 25):

        draw.line([(i, 0), (i - 200, height)], fill=(255, 255, 255, 30), width=2)

    # Fuente

    try:

        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)

    except:

        font = ImageFont.load_default()

    # Texto con rotación y sombra

    x_offset = 40

    for char in codigo:

        angle = random.randint(-15, 15)

        char_img = Image.new("RGBA", (150, 150), (0, 0, 0, 0))

        char_draw = ImageDraw.Draw(char_img)

        # Sombra

        char_draw.text((10, 10), char, font=font, fill=(0, 0, 0, 120))

        # Letra

        char_draw.text((0, 0), char, font=font, fill=(255, 255, 255))

        rotated = char_img.rotate(angle, expand=1)

        img.paste(rotated, (x_offset, 25), rotated)

        x_offset += 70

    buffer = io.BytesIO()

    img.save(buffer, format="PNG")

    buffer.seek(0)

    return codigo, buffer

# ============================

# BOTÓN DE VERIFICACIÓN

# ============================

class VerifyButtonItem(discord.ui.Button):

    def __init__(self, panel_id, label):

        super().__init__(

            label=label,

            emoji="<a:ao_Tick:1485072554879357089>",

            style=discord.ButtonStyle.success,

            custom_id=f"verify_{panel_id}"

        )

        self.panel_id = panel_id

    async def callback(self, interaction: discord.Interaction):

        return

class VerifyButton(discord.ui.View):

    def __init__(self, panel_id, label):

        super().__init__(timeout=None)

        self.add_item(VerifyButtonItem(panel_id, label))

# ============================

# COG PRINCIPAL

# ============================

class VerificationCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # intentos fallidos y cooldowns por (guild_id, panel_id, user_id)

        self.fallos = {}

        self.cooldowns = {}

        data = load_verification()

        for guild_id, panels in data.items():

            for panel_id, cfg in panels.items():

                label = cfg.get("boton", "Verificar")

                bot.add_view(VerifyButton(panel_id, label))

    # ============================

    # CREAR PANEL

    # ============================

    @app_commands.command(

        name="verificacion",

        description="Crear un panel de verificación completo"

    )

    @app_commands.choices(

        tipo=[

            app_commands.Choice(name="Botón", value="normal"),

            app_commands.Choice(name="Captcha", value="captcha")

        ]

    )

    async def verificacion(

        self,

        interaction: discord.Interaction,

        panel_id: str,

        canal: discord.TextChannel,

        canal_logs: discord.TextChannel,

        titulo: str,

        descripcion: str,

        mensaje: str = None,

        imagen_url: str = None,

        rol_dar: discord.Role = None,

        rol_quitar: discord.Role = None,

        texto_boton: str = "Verificar",

        tipo: app_commands.Choice[str] = None,

        texto_captcha: str = "Verifícate por seguridad del servidor",

        max_fallos: int | None = None,

        cooldown_fallos: int | None = None

    ):

        # Validar ID de panel

        if not is_valid_panel_id(panel_id):

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> Ese ID de panel no es válido. Usa solo letras, números, guiones y guiones bajos.",

                ephemeral=True

            )

        # Validar canales

        if not canal or not isinstance(canal, discord.TextChannel):

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> El canal especificado no es válido.",

                ephemeral=True

            )

        if not canal_logs or not isinstance(canal_logs, discord.TextChannel):

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> El canal de logs especificado no es válido.",

                ephemeral=True

            )

        tipo = tipo.value if tipo else "normal"

        guild_id = str(interaction.guild.id)

        data = load_verification()

        if guild_id not in data:

            data[guild_id] = {}

        panel_id = sanitize_panel_id(panel_id.lower())

        data[guild_id][panel_id] = {

            "rol_dar": rol_dar.id if rol_dar else None,

            "rol_quitar": rol_quitar.id if rol_quitar else None,

            "titulo": titulo,

            "descripcion": descripcion,

            "mensaje": mensaje,

            "imagen": imagen_url,

            "boton": texto_boton,

            "tipo": tipo,

            "captcha_texto": texto_captcha,

            "canal_logs": canal_logs.id,

            "max_fallos": max_fallos,

            "cooldown_fallos": cooldown_fallos

        }

        save_verification(data)

        embed = discord.Embed(

            title=titulo,

            description=descripcion,

            color=discord.Color.green()

        )

        if mensaje:

            embed.add_field(name="Información", value=mensaje, inline=False)

        if imagen_url:

            embed.set_image(url=imagen_url)

        view = VerifyButton(panel_id, texto_boton)

        try:

            await canal.send(embed=embed, view=view)

        except:

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> No pude enviar el panel en ese canal. Revisa mis permisos.",

                ephemeral=True

            )

        await interaction.response.send_message(

            "<a:ao_Tick:1485072554879357089> Panel creado correctamente.",

            ephemeral=True

        )

    # ============================

    # ENVIAR PANEL EXISTENTE

    # ============================

    @app_commands.command(

        name="verificacion_enviar",

        description="Enviar un panel de verificación ya creado"

    )

    async def verificacion_enviar(self, interaction: discord.Interaction, panel_id: str, canal: discord.TextChannel):

        # Validar ID de panel

        if not is_valid_panel_id(panel_id):

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> Ese ID de panel no es válido. Inténtalo de nuevo con un ID correcto.",

                ephemeral=True

            )

        # Validar canal

        if not canal or not isinstance(canal, discord.TextChannel):

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> El canal especificado no es válido.",

                ephemeral=True

            )

        guild_id = str(interaction.guild.id)

        data = load_verification()

        panel_id = sanitize_panel_id(panel_id.lower())

        if guild_id not in data or panel_id not in data[guild_id]:

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> Ese panel no existe en este servidor.",

                ephemeral=True

            )

        cfg = data[guild_id][panel_id]

        embed = discord.Embed(

            title=cfg["titulo"],

            description=cfg["descripcion"],

            color=discord.Color.green()

        )

        if cfg.get("mensaje"):

            embed.add_field(name="Información", value=cfg["mensaje"], inline=False)

        if cfg.get("imagen"):

            embed.set_image(url=cfg["imagen"])

        boton = cfg.get("boton", "Verificar")

        view = VerifyButton(panel_id, boton)

        try:

            await canal.send(embed=embed, view=view)

        except:

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> No pude enviar el panel en ese canal. Revisa mis permisos.",

                ephemeral=True

            )

        await interaction.response.send_message(

            "<a:ao_Tick:1485072554879357089> Panel enviado correctamente.",

            ephemeral=True

        )

    # ============================

    # INTERACCIÓN DEL BOTÓN

    # ============================

    @commands.Cog.listener()

    async def on_interaction(self, interaction: discord.Interaction):

        if not interaction.data:

            return

        custom = interaction.data.get("custom_id", "")

        if not custom.startswith("verify_"):

            return

        raw_id = custom.split("_", 1)[1]

        if not is_valid_panel_id(raw_id):

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> El ID de este panel es inválido. Contacta con un administrador.",

                ephemeral=True

            )

        panel_id = sanitize_panel_id(raw_id.lower())

        guild_id = str(interaction.guild.id)

        data = load_verification()

        if guild_id not in data or panel_id not in data[guild_id]:

            return await interaction.response.send_message(

                "<:X_:1476336151835967640> Panel no encontrado. Es posible que haya sido eliminado.",

                ephemeral=True

            )

        cfg = data[guild_id][panel_id]

        rol_dar = interaction.guild.get_role(cfg["rol_dar"]) if cfg.get("rol_dar") else None

        rol_quitar = interaction.guild.get_role(cfg["rol_quitar"]) if cfg.get("rol_quitar") else None

        tipo = cfg.get("tipo", "normal")

        canal_logs = interaction.guild.get_channel(cfg.get("canal_logs"))

        if rol_dar and rol_dar in interaction.user.roles:

            return await interaction.response.send_message(

                "<a:ao_Tick:1485072554879357089> Ya estás verificado.",

                ephemeral=True

            )

        # ============================

        # VERIFICACIÓN NORMAL

        # ============================

        if tipo == "normal":

            try:

                if rol_quitar:

                    await interaction.user.remove_roles(rol_quitar)

                if rol_dar:

                    await interaction.user.add_roles(rol_dar)

                await interaction.response.send_message(

                    "<a:ao_Tick:1485072554879357089> Verificación completada.",

                    ephemeral=True

                )

                await self.enviar_log_verificacion(

                    interaction.user,

                    interaction.guild,

                    canal_logs,

                    rol_dado=rol_dar,

                    rol_quitado=rol_quitar

                )

            except:

                return await interaction.response.send_message(

                    "<:X_:1476336151835967640> No pude asignar los roles. Revisa mis permisos.",

                    ephemeral=True

                )

            return

        # ============================

        # VERIFICACIÓN CON CAPTCHA

        # ============================

        max_fallos = cfg.get("max_fallos")

        cooldown_fallos = cfg.get("cooldown_fallos")

        # Comprobar cooldown antes de mostrar captcha

        key = (guild_id, panel_id, interaction.user.id)

        now = time.time()

        if key in self.cooldowns:

            hasta = self.cooldowns[key]

            if now < hasta:

                restante = int(hasta - now)

                return await interaction.response.send_message(

                    f"<:X_:1476336151835967640> Has superado los intentos permitidos. Podrás volver a intentarlo en **{restante} segundos**.",

                    ephemeral=True

                )

        codigo, imagen = generar_captcha()

        embed = discord.Embed(

            title="<:escudo:1483506514399334441> Verificación con Captcha",

            description=cfg.get("captcha_texto", "Verifícate por seguridad del servidor"),

            color=discord.Color.blue()

        )

        file = discord.File(imagen, filename="captcha.png")

        embed.set_image(url="attachment://captcha.png")

        self_cog = self

        class CaptchaResponder(discord.ui.View):

            def __init__(self):

                super().__init__(timeout=120)

                self.add_item(ResponderButton())

        class ResponderButton(discord.ui.Button):

            def __init__(self):

                super().__init__(

                    label="Responder",

                    style=discord.ButtonStyle.primary,

                    custom_id=f"captcha_reply_{panel_id}"

                )

            async def callback(self, i: discord.Interaction):

                class CaptchaModal(discord.ui.Modal, title="Verificación con Captcha"):

                    def __init__(self):

                        super().__init__()

                        self.input = discord.ui.TextInput(

                            label="Introduce el código",

                            placeholder="Escribe exactamente lo que ves",

                            required=True

                        )

                        self.add_item(self.input)

                    async def on_submit(self, modal_interaction: discord.Interaction):

                        nonlocal codigo, max_fallos, cooldown_fallos, canal_logs

                        g_id = str(modal_interaction.guild.id)

                        u_id = modal_interaction.user.id

                        k = (g_id, panel_id, u_id)

                        ahora = time.time()

                        # Comprobar cooldown otra vez por seguridad

                        if k in self_cog.cooldowns:

                            hasta_local = self_cog.cooldowns[k]

                            if ahora < hasta_local:

                                restante_local = int(hasta_local - ahora)

                                return await modal_interaction.response.send_message(

                                    f"<:X_:1476336151835967640> Has superado los intentos permitidos. Podrás volver a intentarlo en **{restante_local} segundos**.",

                                    ephemeral=True

                                )

                        if self.input.value == codigo:

                            # Acierta: resetear fallos y cooldown

                            if k in self_cog.fallos:

                                del self_cog.fallos[k]

                            if k in self_cog.cooldowns:

                                del self_cog.cooldowns[k]

                            try:

                                if rol_quitar:

                                    await modal_interaction.user.remove_roles(rol_quitar)

                                if rol_dar:

                                    await modal_interaction.user.add_roles(rol_dar)

                                await modal_interaction.response.send_message(

                                    "<a:ao_Tick:1485072554879357089> Verificación completada.",

                                    ephemeral=True

                                )

                                await self_cog.enviar_log_verificacion(

                                    modal_interaction.user,

                                    modal_interaction.guild,

                                    canal_logs,

                                    rol_dado=rol_dar,

                                    rol_quitado=rol_quitar

                                )

                            except:

                                await modal_interaction.response.send_message(

                                    "<:X_:1476336151835967640> No pude asignar los roles. Revisa mis permisos.",

                                    ephemeral=True

                                )

                        else:

                            # Fallo de captcha

                            intentos = self_cog.fallos.get(k, 0) + 1

                            self_cog.fallos[k] = intentos

                            # Si no hay límite configurado, solo mensaje de error

                            if not max_fallos or not cooldown_fallos:

                                return await modal_interaction.response.send_message(

                                    "<:X_:1476336151835967640> **Código incorrecto, inténtalo de nuevo**",

                                    ephemeral=True

                                )

                            # Hay límite configurado

                            if intentos >= max_fallos:

                                # Activar cooldown

                                hasta = ahora + cooldown_fallos

                                self_cog.cooldowns[k] = hasta

                                # Log de intentos fallidos

                                await self_cog.enviar_log_fallos_verificacion(

                                    usuario=modal_interaction.user,

                                    guild=modal_interaction.guild,

                                    canal_logs=canal_logs,

                                    panel_id=panel_id,

                                    intentos=intentos,

                                    cooldown_segundos=cooldown_fallos

                                )

                                restante = int(cooldown_fallos)

                                await modal_interaction.response.send_message(

                                    f"<:X_:1476336151835967640> Has superado el número de intentos permitidos. "

                                    f"Podrás volver a intentarlo en **{restante} segundos**.",

                                    ephemeral=True

                                )

                            else:

                                await modal_interaction.response.send_message(

                                    f"<:X_:1476336151835967640> **Código incorrecto, inténtalo de nuevo** "

                                    f"(Intentos: {intentos}/{max_fallos})",

                                    ephemeral=True

                                )

                await i.response.send_modal(CaptchaModal())

        await interaction.response.send_message(

            embed=embed,

            file=file,

            view=CaptchaResponder(),

            ephemeral=True

        )

    # ============================

    # LOG DE VERIFICACIÓN

    # ============================

    async def enviar_log_verificacion(

        self,

        usuario: discord.Member,

        guild: discord.Guild,

        canal_logs: discord.TextChannel,

        rol_dado=None,

        rol_quitado=None

    ):

        if not canal_logs:

            return

        embed = discord.Embed(

            title="<a:ao_Tick:1485072554879357089> Usuario Verificado",

            color=discord.Color.green()

        )

        embed.add_field(

            name="<:anuncio:1483506577024614660> Usuario",

            value=f"{usuario.mention}",

            inline=False

        )

        embed.add_field(

            name="<:link:1483506560935268452> ID del usuario",

            value=str(usuario.id),

            inline=False

        )

        embed.add_field(

            name="<:escudo:1483506514399334441> Bot",

            value=self.bot.user.mention,

            inline=False

        )

        if rol_dado:

            embed.add_field(

                name="<:regalo:1483506548495093957> Rol asignado",

                value=rol_dado.mention,

                inline=False

            )

        else:

            embed.add_field(

                name="<:regalo:1483506548495093957> Rol asignado",

                value="Ninguno",

                inline=False

            )

        if rol_quitado:

            embed.add_field(

                name="<:basura:1483506530715439104> Rol retirado",

                value=rol_quitado.mention,

                inline=False

            )

        else:

            embed.add_field(

                name="<:basura:1483506530715439104> Rol retirado",

                value="Ninguno",

                inline=False

            )

        embed.add_field(

            name="<:discord:1483506738954244258> Servidor",

            value=guild.name,

            inline=False

        )

        if usuario.avatar:

            embed.set_thumbnail(url=usuario.avatar.url)

        await canal_logs.send(embed=embed)

    # ============================

    # LOG DE INTENTOS FALLIDOS / COOLDOWN

    # ============================

    async def enviar_log_fallos_verificacion(

        self,

        usuario: discord.Member,

        guild: discord.Guild,

        canal_logs: discord.TextChannel,

        panel_id: str,

        intentos: int,

        cooldown_segundos: int

    ):

        if not canal_logs:

            return

        ahora = datetime.datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")

        embed = discord.Embed(

            title="<a:warning:1485072594012209354> Intentos fallidos de verificación",

            color=discord.Color.red()

        )

        embed.add_field(

            name="<:anuncio:1483506577024614660> Usuario",

            value=f"{usuario.mention} (`{usuario.id}`)",

            inline=False

        )

        embed.add_field(

            name="<:link:1483506560935268452> Panel",

            value=panel_id,

            inline=False

        )

        embed.add_field(

            name="<:basura:1483506530715439104> Intentos fallidos",

            value=str(intentos),

            inline=False

        )

        embed.add_field(

            name="<:escudo:1483506514399334441> Acción",

            value=f"Cooldown activado ({cooldown_segundos}s)",

            inline=False

        )

        embed.add_field(

            name="<:reloj:1485698211795701961> Hora",

            value=ahora + " (UTC)",

            inline=False

        )

        embed.add_field(

            name="<:discord:1483506738954244258> Servidor",

            value=guild.name,

            inline=False

        )

        if usuario.avatar:

            embed.set_thumbnail(url=usuario.avatar.url)

        await canal_logs.send(embed=embed)

# ============================

# SETUP DEL COG

# ============================

async def setup(bot):

    await bot.add_cog(VerificationCog(bot))