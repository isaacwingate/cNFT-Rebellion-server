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
from wallet_interaction import *

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

if hours == 0:
	hours = 24
mins += hours * 60

if hours >= 21:
    mins -= 21 * 60
elif hours >= 9:
    mins -= 9 * 60

time_remaining = 720 - mins

#################### END INIT ####################

async def dm_user(uid, msg, field1=None, field2=None, colour=discord.Colour.blue()):
	user = discord_client.get_user(int(uid))

	emb=discord.Embed(description=msg, colour = colour)
	emb.set_author(name="Verification Bot", icon_url=PFP)

	if field1:
		emb.add_field(name=str(field1[0]), value=str(field1[1]), inline=False)

	if field2:
		emb.add_field(name=str(field2[0]), value=str(field2[1]), inline=False)

	await user.send(embed=emb)

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
	users = get_all_members()
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

#################### END INIT DISCORD BOT ####################

@discord_client.command()
@is_dm()
async def reset(ctx):
	guild = discord_client.get_guild(SERVER_ID)

	role = discord.utils.get(guild.roles, name=ROLE_NAME)

	user_id = ctx.author.id
	member = guild.get_member(int(user_id))
	username = str(ctx.author.name)

	if user_id in user_ids:
	    user_ids.remove(user_id)
	await removeMemberID(user_id)
	await removeTx(user_id)

	for r_name in ROLE_NAME:
		if r_name in [x.name for x in member.roles]:
			role = discord.utils.get(guild.roles, name=r_name)         # remove Con role
			await member.remove_roles(role)

	#await ctx.send('Reset succesfully! Type /join to try again.')
	await dm_user(user_id, "Reset succesful! Type /join to try again.", None, None, discord.Colour.green())
	print_log(username + " has used /reset")
	return

#################### /join Command ####################
@discord_client.command()
@is_dm()
async def verify(ctx):
	await join(ctx)

@discord_client.command()
@is_dm()
async def join(ctx):
	if not active:
		return

	guild = discord_client.get_guild(SERVER_ID)
	# Get user details
	user_id = ctx.author.id
	username = str(ctx.author.name)
	member = guild.get_member(user_id)

	user = findMember(user_id)
	if user:
		url = "https://pool.pm/"+str(user['addr'])
		await dm_user(user_id, "You have already been verified!", ["The wallet currently linked to your account is: ",url], ["/reset","Use this command if you wish to register a new wallet."])
		return


	#check if user has outstanding Tx
	cur_addr = searchPendingUsr(user_id)
	if cur_addr:
		# user has a pending Txn
		print_log(username + " has current session, sending same addr")
		await dm_user(user_id, "You already have a pending verification",
 		["The bot is awaiting payment of "+str(cur_addr['amount'])+" on this addr:",str(cur_addr['addr'])],["Time remaining:","You have " + str(TXN_TIME_LIMIT - cur_addr['attempts']) + " minutes..."])
	else:
		print_log(username + " has started verification process")

		w_mutex.acquire()
		# CRITICAL SECTION START
		if len(discord_client.paymentAddr_queue) <= 0:
			discord_client.paymentAddr_queue = initQueue()

		paymentAddr = discord_client.paymentAddr_queue.pop(0)
		# CRITICAL SECTION END
		w_mutex.release()

		# get random amount
		amount = round(rand.uniform(2.0000, 3.5000),4)

		# Notify user
		await dm_user(user_id, "Verification Process Initiated",
 		["Please send EXACTLY " + str(amount) + " ada to the following address: ",str(paymentAddr)],["Time remaining: ","You have " + str(TXN_TIME_LIMIT) + " minutes..."])

		print_log(str(username) + " was assigned: " +str(paymentAddr))
		await insertPendingTx(user_id, username, paymentAddr, amount)


#################### END /join Command ####################

#################### Check Pending Tx's ####################
@discord_client.event
async def on_check_pending_tx():
	guild = discord_client.get_guild(SERVER_ID)

	print_log("Checking pending tx's.")

	pendingAddr = getAllPendingAddr()

	for a in pendingAddr:
		usr_addr, txn = checkForPayment(a['addr'], a['amount'])

		if not txn:
			# increment attempts
			expired_user_id = await checkAttempts(str(a['addr']), a['amount'])
			if expired_user_id:
				await dm_user(expired_user_id, "⚠️⚠️ Address has expired, **DO NOT SEND ADA !!** ⚠️⚠️ Please use /join to try again!",None,None, discord.Colour.red())
		else:
			username = a['username']
			user_id = a['user_id']
			amount = a['amount']
			# insert refund into DB
			await insertRefund(username, str(usr_addr), amount-GAS)

			# get users stake addr
			stakeAddr = getStakeAddr(usr_addr)

			# search for assets
			assetCount = searchAddr(stakeAddr)

			# if no assets are found
			if assetCount == 0:
				print_log(str(username) + " Does not have a Kong")
				await dm_user(user_id, "Could not find the required NFT in your wallet, try again later.", None, None, discord.Colour.red())
			else:
				# criteria for roles
				if assetCount <= 4:
					role = discord.utils.get(guild.roles, name=ROLE_NAME[0])
					r_name = ROLE_NAME[0]
				elif assetCount <= 10:
					role = discord.utils.get(guild.roles, name=ROLE_NAME[1])
					r_name = ROLE_NAME[1]
				elif assetCount <= 20:
					role = discord.utils.get(guild.roles, name=ROLE_NAME[2])
					r_name = ROLE_NAME[2]
				elif assetCount <= 49:
					role = discord.utils.get(guild.roles, name=ROLE_NAME[3])
					r_name = ROLE_NAME[3]
				elif assetCount <= 99:
					role = discord.utils.get(guild.roles, name=ROLE_NAME[4])
					r_name = ROLE_NAME[4]
				else:
					role = discord.utils.get(guild.roles, name=ROLE_NAME[5])
					r_name = ROLE_NAME[5]

				member = guild.get_member(user_id)

				if member:
					await member.add_roles(role)
					await insertMember(user_id, str(username), str(stakeAddr), str(txn), str(r_name), assetCount)
					print_log(str(member.name) + " has " + str(assetCount) + " tokens, " + str(r_name) + " role given.")
					await dm_user(user_id, "You have been verified!",["Asset Count: ",str(assetCount)],["Role Given",str(r_name)], discord.Colour.green())
				else:
					print_log("Couldn't find member obj for " + str(username))

#################### END Check Pending Tx's ####################

#################### Resweep ####################
@discord_client.event
async def on_resweep():
	guild = discord_client.get_guild(SERVER_ID)
	
	print_log("Initiating resweep.")
	
	allMembers = get_all_members()

	# iterate through all members
	for user in allMembers:
		# search for assets
		assetCount = searchAddr(user['addr'])
		role = discord.utils.get(guild.roles, name=str(user['role']))
		member = guild.get_member(int(user['id']))
		if member:
			if assetCount == 0:
				await member.remove_roles(role)
				
				# remove record from DB
				await removeMember(user['addr'])
				print_log(str(user['name']) + " has been removed from the club, address: " + str(user['addr']))
			else:
				cur_role = user['role']
				cur_cnt = user['ass_cnt']

				if assetCount != cur_cnt:

					if assetCount <= 4:
						role = discord.utils.get(guild.roles, name=ROLE_NAME[0])
						r_name = ROLE_NAME[0]
					elif assetCount <= 10:
						role = discord.utils.get(guild.roles, name=ROLE_NAME[1])
						r_name = ROLE_NAME[1]
					elif assetCount <= 20:
						role = discord.utils.get(guild.roles, name=ROLE_NAME[2])
						r_name = ROLE_NAME[2]
					elif assetCount <= 49:
						role = discord.utils.get(guild.roles, name=ROLE_NAME[3])
						r_name = ROLE_NAME[3]
					elif assetCount <= 99:
						role = discord.utils.get(guild.roles, name=ROLE_NAME[4])
						r_name = ROLE_NAME[4]
					else:
						role = discord.utils.get(guild.roles, name=ROLE_NAME[5])
						r_name = ROLE_NAME[5]

					if r_name != cur_role:
						old_role = discord.utils.get(guild.roles, name=cur_role)
						await member.remove_roles(old_role)
						await member.add_roles(role)

						await updateRoleResweep(user['id'], r_name, assetCount)
						print_log(str(user['name'] + " role has changed from " + str(old_role) + " to " + str(r_name)))

#################### END Resweep ####################



if __name__ == "__main__":
	init_discord_bot()
	print_log(str(time_remaining) + " until next resweep.")
	while True:
		if active:
			 
			mins += 1
			if mins == 720:
				mins = 0
				discord_client.dispatch("resweep") #send this event to bot every half a day
			else:
				discord_client.dispatch("check_pending_tx") #send this event to bot every minute
			sleep(60)
			