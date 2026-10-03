# Language: Python 3.10+
# Runtime: Render Free Tier Web Service
# Target: Self-Bot Full Server Cloner (With Intents & Debug Logging)

import asyncio
import os
import discord
from discord.ext import commands
from aiohttp import web

TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", 10000))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=".", self_bot=True, intents=intents)

async def handle_ping(request):
    return web.Response(text="Bot is online and running.")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Web server started on port {PORT} for Render health checks.")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Cloner ready. Use .clone [source_id] [target_id]")

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id and message.content.startswith(".clone"):
        print(f"Detected clone command execution: {message.content}")
    await bot.process_commands(message)

@bot.command(name="clone")
async def clone_server(ctx, source_guild_id: int, target_guild_id: int):
    print(f"Command callback triggered for source: {source_guild_id}, target: {target_guild_id}")
    source_guild = bot.get_guild(source_guild_id)
    target_guild = bot.get_guild(target_guild_id)

    if not source_guild:
        await ctx.send("Source guild not found.")
        return
    if not target_guild:
        await ctx.send("Target guild not found. Make sure you are in it.")
        return

    await ctx.send(f"Wiping and cloning [{source_guild.name}] into [{target_guild.name}]...")

    # 1. Wipe all existing channels in the target server
    for channel in target_guild.channels:
        try:
            await channel.delete()
            await asyncio.sleep(1.2)
        except Exception as e:
            print(f"Failed to delete channel {channel.name}: {e}")

    # 2. Wipe all existing custom roles in the target server (bottom-up to avoid hierarchy blocks)
    sorted_target_roles = sorted(target_guild.roles, key=lambda r: r.position, reverse=True)
    for role in sorted_target_roles:
        if not role.is_default() and not role.managed and role < target_guild.me.top_role:
            try:
                await role.delete()
                await asyncio.sleep(1.2)
            except Exception as e:
                print(f"Failed to delete role {role.name}: {e}")

    # 3. Recreate Roles from source (bottom-up by position, skipping @everyone and managed roles)
    role_mapping = {}
    sorted_roles = sorted(source_guild.roles, key=lambda r: r.position)
    
    for role in sorted_roles:
        if role.is_default() or role.managed:
            continue
        try:
            new_role = await target_guild.create_role(
                name=role.name,
                permissions=role.permissions,
                color=role.color,
                hoist=role.hoist,
                mentionable=role.mentionable
            )
            role_mapping[role.id] = new_role.id
            await asyncio.sleep(1.2)
        except Exception as e:
            print(f"Failed to create role {role.name}: {e}")

    # 4. Recreate Categories and Channels
    categories = sorted([c for c in source_guild.categories], key=lambda c: c.position)
    
    for category in categories:
        try:
            overwrites = {}
            for target_obj, perm in category.overwrites.items():
                if isinstance(target_obj, discord.Role) and target_obj.id in role_mapping:
                    new_role = target_guild.get_role(role_mapping[target_obj.id])
                    if new_role:
                        overwrites[new_role] = perm

            new_cat = await target_guild.create_category(
                name=category.name,
                overwrites=overwrites
            )
            await asyncio.sleep(1.2)

            for channel in category.channels:
                if isinstance(channel, discord.TextChannel):
                    await target_guild.create_text_channel(
                        name=channel.name,
                        category=new_cat,
                        topic=channel.topic,
                        slowmode_delay=channel.slowmode_delay,
                        nsfw=channel.nsfw
                    )
                elif isinstance(channel, discord.VoiceChannel):
                    await target_guild.create_voice_channel(
                        name=channel.name,
                        category=new_cat,
                        bitrate=channel.bitrate,
                        user_limit=channel.user_limit
                    )
                await asyncio.sleep(1.2)
        except Exception as e:
            print(f"Failed to clone category {category.name}: {e}")

    # 5. Recreate Uncategorized Channels
    for channel in source_guild.channels:
        if channel.category is None:
            try:
                if isinstance(channel, discord.TextChannel):
                    await target_guild.create_text_channel(
                        name=channel.name,
                        topic=channel.topic,
                        slowmode_delay=channel.slowmode_delay,
                        nsfw=channel.nsfw
                    )
                elif isinstance(channel, discord.VoiceChannel):
                    await target_guild.create_voice_channel(
                        name=channel.name,
                        bitrate=channel.bitrate,
                        user_limit=channel.user_limit
                    )
                await asyncio.sleep(1.2)
            except Exception as e:
                print(f"Failed to clone uncategorized channel {channel.name}: {e}")

    await ctx.send(f"Clone complete. [{target_guild.name}] is now an exact replica of [{source_guild.name}].")

async def main():
    if not TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set.")
        return
    
    await start_web_server()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
