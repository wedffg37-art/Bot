import discord
from discord.ext import commands, tasks
import os
import traceback
from flask import Flask
import sys
import aiohttp
import asyncio
from dotenv import load_dotenv
import threading

# Initialize environment variables
load_dotenv()

# Flask Setup
app = Flask(__name__)
bot_name = "Loading..."

@app.route('/')
def home():
    """Health check endpoint for Render"""
    return f"Bot {bot_name} is operational"

def run_flask():
    """Run Flask with Render-compatible settings"""
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Discord Bot Setup
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("Missing TOKEN in environment")

class Bot(commands.Bot):
    def __init__(self):
        # Configure minimal required intents
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.session = None

    async def setup_hook(self):
        """Initialize bot components"""
        self.session = aiohttp.ClientSession()
        
        # Load cogs
        try:
            await self.load_extension("cogs.infoCommands")
            print("✅ Successfully loaded InfoCommands cog")
        except Exception as e:
            print(f"❌ Failed to load cog: {e}")
            traceback.print_exc()
        
        await self.tree.sync()
        self.update_status.start()
        self.keep_alive.start()  # <-- بدء مهمة Keep-Alive

    async def on_ready(self):
        """When bot connects to Discord"""
        global bot_name
        bot_name = str(self.user)
        
        print(f"\n🔗 Connected as {bot_name}")
        print(f"🌐 Serving {len(self.guilds)} servers")
        
        # Start Flask if running on Render
        if os.environ.get('RENDER'):
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            print("🚀 Flask server started in background")

    @tasks.loop(minutes=5)
    async def update_status(self):
        """Update bot presence periodically"""
        try:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers"
            )
            await self.change_presence(activity=activity)
        except Exception as e:
            print(f"⚠️ Status update failed: {e}")

    @update_status.before_loop
    async def before_status_update(self):
        await self.wait_until_ready()

    @tasks.loop(minutes=1)
    async def keep_alive(self):
        """Ping Flask to keep Render awake every 1 minute"""
        if self.session:
            try:
                url = "https://bot-info-ff.onrender.com"  # رابط سيرفرك
                async with self.session.get(url) as response:
                    print(f"💡 Keep-Alive ping status: {response.status}")
            except Exception as e:
                print(f"⚠️ Keep-Alive failed: {e}")

    async def close(self):
        """Cleanup on shutdown"""
        if self.session:
            await self.session.close()
        await super().close()

async def main():
    bot = Bot()
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        print(f"⚠️ Critical error: {e}")
        traceback.print_exc()
        await bot.close()

if __name__ == "__main__":
    # Special handling for Render's environment
    if os.environ.get('RENDER'):
        asyncio.run(main())
    else:
        bot = Bot()
        bot.run(TOKEN)
