# Language: Python 3.10+
# Runtime: Render Free Tier Web Service
# Target: Self-Bot Server Cloner (Target-Existing Mode)

import asyncio
import os
import discord
from discord.ext import commands
from aiohttp import web

TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", 10000))

bot = commands.Bot(command_prefix=".", self_bot=True)

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

@bot.command(name="clone")
async def clone_server(ctx, source_guild_id: int, target_guild_id: int):
    source_guild = bot.get_guild(source_guild_id)
    target_guild = bot.get_guild(target_guild_id)

    if not source_guild:
        await ctx.send("Source guild not found or your account is not a member of it.")
        return
    if not target_guild:
        await ctx.send("Target guild not found. Make sure you are in the destination server and have admin rights.")
        return

    await ctx.send(f"Cloning [{source_guild.name}] into [{target_guild.name}]... Please wait.")

    # 1. Wipe default channels in the target server
    for channel in target_guild.channels:
        try:
            await channel.delete()
            await asyncio.sleep(1.2)
        except Exception as e:
            print(f"Failed to delete channel {channel.name}: {e}")

    # 2. Recreate Roles (sorted by position, skipping @everyone and managed roles)
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

    # 3. Recreate Categories and Channels
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

    # 4. Recreate Uncategorized Channels
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

    await ctx.send(f"Successfully cloned [{source_guild.name}] into [{target_guild.name}]!")

async def main():
    if not TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set.")
        return
    
    await start_web_server()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
