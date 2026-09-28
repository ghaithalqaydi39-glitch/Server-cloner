# Discord Server Cloner Self-Bot

A Python self-bot utilizing `discord.py-self` to clone Discord server structures (roles, categories, channels) into a brand-new server. Configured with an integrated aiohttp web server for deployment on Render's free tier.

## Deployment Setup
1. Fork or push this repository to GitHub.
2. Create a new **Web Service** on Render, linking this repository.
3. Set the Environment to Python 3, Build Command to `pip install -r requirements.txt`, and Start Command to `python main.py`.
4. Add your user account token under Environment Variables as `DISCORD_TOKEN`.
