import discord
from discord_components import ComponentsBot
from discord.ext import commands
from discord.utils import get
import asyncio
from datetime import datetime
import warnings
from threading import Thread
from time import sleep
from threading import Lock
import random as rand

from server_variables import *
from helper_funcs import *
from handle_db import *
from wallet_interaction import initQueue()

w_mutex = Lock()

#################### INIT ####################

rand.seed(datetime.now())
warnings.filterwarnings("ignore")
intents = discord.Intents(members = True, messages=True, guilds=True, presences=True)
user_ids = []
active = False

discord_client = ComponentsBot("/",intents = intents)
discord_client.paymentAddr_queue = initQueue()

# Init resweep for 9am / 9pm
now = datetime.now()
hours, mins = int(now.strftime("%H: %M")[:2]), int(now.strftime("%H: %M")[3:6])
mins += hours * 60

if hours >= 21:
    mins -= 21 * 60
elif hours >= 9:
    mins -= 9 * 60

time_remaining = 720 - mins

#################### END INIT ####################

#################### ADMIN COMMANDS ####################
@discord_client.command()
@is_owner()
async def start(ctx):
	global active
	active = True
	print_log("VERIFICATION GOING ACTIVE")
	await ctx.send("OK")
	return

@discord_client.command()
@is_owner()
async def stop(ctx):
	global active
	active = False
	print_log("STOPPING VERIFICATION ACTIVITIES")
	await ctx.send("OK")

@discord_client.command()
@is_owner()
async def random(ctx):
	users = get_all_addr()
	index = rand.randint(0, (len(users)-1))
	user = users[index]

	emb=discord.Embed(Title="Random Holder", colour = discord.Colour.green())
	emb.add_field(name="ID", value=str(user['id']), inline=False)
	emb.add_field(name="Username", value=str(user['name']), inline=False)
	emb.add_field(name="Address", value=str(user['addr']), inline=False)

	await ctx.author.send(embed=emb)
	return

# view addr available
@discord_client.command()
@is_owner()
async def addr(ctx):
	print_log('Free addr: ' + str(len(discord_client.paymentAddr_queue)))

#################### END ADMIN COMMANDS ####################

#################### INIT DISCORD BOT ####################
def init_discord_bot():
    loop = asyncio.get_event_loop()
    loop.create_task(client_start())
    t = Thread(target=loop.run_forever)
    t.daemon = True #terminates when main thread terminates. this is important
    t.start()

async def client_start():
    await discord_client.start(DISCORD_TOKEN)  

@discord_client.event
async def on_ready():
	print("Discord bot logged in as: %s, %s" % (discord_client.user.name, discord_client.user.id))

if __name__ == "__main__":
	init_discord_bot()
	print_log(str(time_remaining) + " until next resweep.")

	while True:
		sleep(60) 
		if active:
			mins += 1
			if mins == 720:
				mins = 0
				discord_client.dispatch("resweep") #send this event to bot every half a day
			else:
				discord_client.dispatch("check_pending_tx") #send this event to bot every minute

#################### END INIT DISCORD BOT ####################

#################### /join Command ####################
@discord_client.command()
@is_dm()
async def join(ctx):
	user_id = ctx.author.id
	username = str(ctx.author.name)

	print_log(username + " has started verification process")

#################### END /join Command ####################

#################### Check Pending Tx's ####################
@discord_client.command()
async def on_check_pending_tx(ctx):
	print_log("Checking pending tx's.")

#################### END Check Pending Tx's ####################

#################### Resweep ####################
@discord_client.command()
async def resweep(ctx):
	print_log("Resweep Initiated")

#################### END Resweep ####################