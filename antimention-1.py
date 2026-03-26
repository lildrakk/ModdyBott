import discord

from discord.ext import commands

from discord import app_commands

import json, os, time

from datetime import timedelta

# Ruta correcta para Render

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "antimention.json")

# ============================================================

# CONFIG SEGURO (PERSISTENTE)

# ============================================================

def load_config():

    if not os.path.exists(CONFIG_FILE):

        return {}

    try:

        with open(CONFIG_FILE, "r") as f:

            return json.load(f)

    except:

        return {}

def save_config(data):

    tmp = CONFIG_FILE + ".tmp"

    with open(tmp, "w") as f:

        json.dump(data, f, indent=4)

    os.replace(tmp, CONFIG_FILE)

# ============================================================

# COG ANTI‑MENTION PRO

# ============================================================

class AntiMention(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.config = load_config()

        self.cooldowns = {}

    # --------------------------------------------------------

    # CONFIG POR SERVIDOR

    # --------------------------------------------------------

    def ensure_guild(self, guild_id: int):

        gid = str(guild_id)

        if gid not in self.config:

            self.config[gid] = {

                "enabled": False,

                "accion": "warn",

                "mute_time": 600,

                "cooldown": 3,

                "logs": None,

                "limit_users": 3,

                "limit_roles": 3,

                "limit_everyone": 1,

                "blocked_users": [],

                "blocked_roles": [],

                "whitelist_users": [],

                "whitelist_roles": [],

                "whitelist_channels": []

            }

            save_config(self.config)

        return self.config[gid]

    # ============================================================

    # COMANDO PRINCIPAL /antimention

    # ============================================================

    @app_commands.command(name="antimention", description="Configura el Anti‑Mention.")

    @app_commands.describe(

        activar="True/False para activar o desactivar",

        accion="Acción a aplicar cuando se detecta abuso de menciones",

        limite_usuarios="Límite de menciones a usuarios",

        limite_roles="Límite de menciones a roles",

        limite_everyone="0 o 1 para permitir @everyone",

        cooldown="Cooldown entre detecciones",

        logs="Canal de logs"

    )

    @app_commands.choices(

        accion=[

            app_commands.Choice(name="Warn", value="warn"),

            app_commands.Choice(name="Mute", value="mute"),

            app_commands.Choice(name="Kick", value="kick"),

            app_commands.Choice(name="Ban", value="ban")

        ]

    )

    async def antimention_cmd(

        self,

        interaction: discord.Interaction,

        activar: bool = None,

        accion: str = None,

        limite_usuarios: int = None,

        limite_roles: int = None,

        limite_everyone: int = None,

        cooldown: int = None,

        logs: discord.TextChannel = None

    ):

        guild = interaction.guild

        cfg = self.ensure_guild(guild.id)

        if activar is not None:

            cfg["enabled"] = activar

        if accion is not None:

            cfg["accion"] = accion

        if limite_usuarios is not None:

            cfg["limit_users"] = max(1, limite_usuarios)

        if limite_roles is not None:

            cfg["limit_roles"] = max(1, limite_roles)

        if limite_everyone is not None:

            cfg["limit_everyone"] = max(0, limite_everyone)

        if cooldown is not None:

            cfg["cooldown"] = max(0, cooldown)

        if logs is not None:

            cfg["logs"] = logs.id

        save_config(self.config)

        embed = discord.Embed(

            title="<a:ao_Tick:1485072554879357089> Configuración Anti‑Mention actualizada",

            color=discord.Color.yellow()

        )

        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)

        embed.add_field(name="Acción", value=cfg["accion"], inline=False)

        embed.add_field(name="Límite usuarios", value=cfg["limit_users"], inline=True)

        embed.add_field(name="Límite roles", value=cfg["limit_roles"], inline=True)

        embed.add_field(name="Límite everyone", value=cfg["limit_everyone"], inline=True)

        embed.add_field(name="Cooldown", value=cfg["cooldown"], inline=True)

        embed.add_field(name="Logs", value=f"<#{cfg['logs']}>" if cfg["logs"] else "Ninguno", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================================================

    # NUEVOS COMANDOS: WHITELIST

    # ============================================================

    @app_commands.command(name="antimention_whitelist", description="Añade o quita usuarios de la whitelist.")

    @app_commands.describe(accion="add/remove", usuario="Usuario a modificar")

    @app_commands.choices(

        accion=[

            app_commands.Choice(name="Añadir", value="add"),

            app_commands.Choice(name="Eliminar", value="remove")

        ]

    )

    async def antimention_whitelist(self, interaction: discord.Interaction, accion: str, usuario: discord.User):

        guild = interaction.guild

        cfg = self.ensure_guild(guild.id)

        if accion == "add":

            if usuario.id not in cfg["whitelist_users"]:

                cfg["whitelist_users"].append(usuario.id)

        else:

            if usuario.id in cfg["whitelist_users"]:

                cfg["whitelist_users"].remove(usuario.id)

        save_config(self.config)

        await interaction.response.send_message(

            f"<:link:1483506560935268452> `{usuario}` **{accion}** en whitelist.",

            ephemeral=True

        )

    # ============================================================

    # NUEVOS COMANDOS: BLACKLIST

    # ============================================================

    @app_commands.command(name="antimention_blacklist", description="Añade o quita usuarios de la blacklist.")

    @app_commands.describe(accion="add/remove", usuario="Usuario a modificar")

    @app_commands.choices(

        accion=[

            app_commands.Choice(name="Añadir", value="add"),

            app_commands.Choice(name="Eliminar", value="remove")

        ]

    )

    async def antimention_blacklist(self, interaction: discord.Interaction, accion: str, usuario: discord.User):

        guild = interaction.guild

        cfg = self.ensure_guild(guild.id)

        if accion == "add":

            if usuario.id not in cfg["blocked_users"]:

                cfg["blocked_users"].append(usuario.id)

        else:

            if usuario.id in cfg["blocked_users"]:

                cfg["blocked_users"].remove(usuario.id)

        save_config(self.config)

        await interaction.response.send_message(

            f"<:link:1483506560935268452> `{usuario}` **{accion}** en blacklist.",

            ephemeral=True

        )

    # ============================================================

    # DETECCIÓN DE MENCIONES (MEJORADA)

    # ============================================================

    @commands.Cog.listener()

    async def on_message(self, message: discord.Message):

        if not message.guild or message.author.bot:

            return

        guild = message.guild

        cfg = self.ensure_guild(guild.id)

        user = message.author

        content = message.content

        if not cfg["enabled"]:

            return

        # WHITELIST

        if user.id in cfg.get("whitelist_users", []):

            return

        if any(r.id in cfg.get("whitelist_roles", []) for r in user.roles):

            return

        if message.channel.id in cfg.get("whitelist_channels", []):

            return

        # COOLDOWN

        now = time.time()

        if user.id in self.cooldowns and now - self.cooldowns[user.id] < cfg["cooldown"]:

            return

        self.cooldowns[user.id] = now

        # DETECCIÓN REAL DE MENCIONES

        user_mentions = message.mentions

        role_mentions = message.role_mentions

        manual_user_mentions = content.count("<@")

        manual_role_mentions = content.count("<@&")

        total_user_mentions = len(user_mentions) + manual_user_mentions

        total_role_mentions = len(role_mentions) + manual_role_mentions

        # BLOQUEADOS

        if user.id in cfg["blocked_users"]:

            return await self.apply_action(message, "Usuario en blacklist")

        if any(u.id in cfg["blocked_users"] for u in user_mentions):

            return await self.apply_action(message, "Mención a usuario bloqueado")

        if any(r.id in cfg["blocked_roles"] for r in role_mentions):

            return await self.apply_action(message, "Mención a rol bloqueado")

        # LÍMITES

        if total_user_mentions > cfg["limit_users"]:

            return await self.apply_action(message, "Exceso de menciones a usuarios")

        if total_role_mentions > cfg["limit_roles"]:

            return await self.apply_action(message, "Exceso de menciones a roles")

        # EVERYONE / HERE

        if ("@everyone" in content or "@here" in content) and cfg["limit_everyone"] < 1:

            return await self.apply_action(message, "Uso de @everyone/@here")

    # ============================================================

    # APLICAR SANCIÓN

    # ============================================================

    async def apply_action(self, message: discord.Message, reason: str):

        guild = message.guild

        cfg = self.ensure_guild(guild.id)

        user = message.author

        action = cfg["accion"]

        try:

            await message.delete()

        except:

            pass

        aviso = discord.Embed(

            title="<a:warn:1483506607265419466> Mención no permitida",

            description=f"{user.mention}, ese usuario/rol está **prohibido** ser mencionado.",

            color=discord.Color.orange()

        )

        try:

            await message.channel.send(user.mention, embed=aviso, delete_after=6)

        except:

            pass

        if cfg["logs"]:

            ch = guild.get_channel(cfg["logs"])

            if ch:

                embed = discord.Embed(

                    title="<a:alarma:1476336115354046607> Log Anti‑Mention",

                    description=f"Usuario: {user.mention}\nRazón: `{reason}`",

                    color=discord.Color.blue()

                )

                await ch.send(embed=embed)

        sancionado = False

        try:

            if action == "ban":

                await guild.ban(user, reason=f"Anti‑Mention: {reason}")

            elif action == "kick":

                await guild.kick(user, reason=f"Anti‑Mention: {reason}")

            elif action == "mute":

                await user.timeout(

                    discord.utils.utcnow() + timedelta(seconds=cfg["mute_time"]),

                    reason=f"Anti‑Mention: {reason}"

                )

            sancionado = True

        except:

            sancionado = False

        if not sancionado:

            embed = discord.Embed(

                title="<a:warn:1483506607265419466> No se pudo aplicar sanción",

                description=f"Detecté abuso de menciones de {user.mention}, pero no tengo permisos.",

                color=discord.Color.yellow()

            )

        else:

            embed = discord.Embed(

                title="<a:advertencia:1483506898509758690> Sanción aplicada",

                description=f"Usuario: {user.mention}\nAcción: **{action}**\nRazón: {reason}",

                color=discord.Color.red()

            )

        await message.channel.send(embed=embed)

# ============================================================

# SETUP

# ============================================================

async def setup(bot):

    await bot.add_cog(AntiMention(bot))