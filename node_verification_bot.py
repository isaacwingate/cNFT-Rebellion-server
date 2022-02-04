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



#################### END INIT ####################

async def dm_user(uid, msg, fields=[], colour=discord.Colour.blue()):
	user = discord_client.get_user(int(uid))

	emb=discord.Embed(description=msg, colour = colour)
	emb.set_author(name="CyclR Verification Bot", icon_url=PFP)

	for x in fields:
		emb.add_field(name=str(x[0]), value=str(x[1]), inline=False)

	await user.send(embed=emb)

#################### ADMIN COMMANDS ####################
@discord_client.command()
@is_admin_owner()
async def instructions(ctx):
	emb=discord.Embed(title="How to verify!", description="Please see the commands below to learn how to verify. You will be required to send a specific amount of ADA to a unique address to confirm you own the wallet.", colour = discord.Colour.blue())
	emb.set_author(name="CyclR Verification Bot", icon_url=PFP)
	emb.add_field(name="Will i be refunded?", value="Yes, you will be refunded the ADA you sent -GAS.", inline=False)
	emb.add_field(name="/join", value="Dm me this command to start the verification process.", inline=True)
	emb.add_field(name="/reset", value="Dm me this command if you are already registered and wish to register a different wallet.", inline=True)
	emb.set_footer(text="Created by Isaac#1277")
	await ctx.channel.send(embed=emb)

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

	if ROLE_NAME.lower() in [x.name.lower() for x in member.roles]:
		role = discord.utils.get(guild.roles, name=ROLE_NAME)         # remove Con role
		await member.remove_roles(role)

	#await ctx.send('Reset succesfully! Type /join to try again.')
	await dm_user(user_id, "Reset succesful! Type /join to try again.", [], discord.Colour.green())
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
		await dm_user(user_id, "You have already been verified!", [["The wallet currently linked to your account is: ",url], ["/reset","Use this command if you wish to register a new wallet."]])
		return


	#check if user has outstanding Tx
	cur_addr = searchPendingUsr(user_id)
	if cur_addr:
		# user has a pending Txn
		print_log(username + " has current session, sending same addr")
		await dm_user(user_id, "You already have a pending verification",
 		[["The bot is awaiting payment of "+str(cur_addr['amount'])+" on this addr:",str(cur_addr['addr'])],["Time remaining:","You have " + str(TXN_TIME_LIMIT - cur_addr['attempts']) + " minutes..."]])
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
 		[["Please send EXACTLY " + str(amount) + " ada to the following address: ",str(paymentAddr)],["Time remaining: ","You have " + str(TXN_TIME_LIMIT) + " minutes..."]])

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
				await dm_user(expired_user_id, "⚠️⚠️ Address has expired, **DO NOT SEND ADA !!** ⚠️⚠️ Please use /join to try again!",[], discord.Colour.red())
		else:
			username = a['username']
			user_id = a['user_id']
			amount = a['amount']
			# insert refund into DB
			await insertRefund(username, str(usr_addr), amount-GAS)

			# get users stake addr
			stakeAddr = getStakeAddr(usr_addr)

			# check if wallet exists
			if findStakeAddr(stakeAddr):
				print_log(str(username) + " Wallet already registered: " + str(stakeAddr))
				await dm_user(user_id, "Your wallet has already been registered.", ["Reset Wallet","Use /reset to reset the wallet attached to your account."], discord.Colour.red())
				return

			#testing purpose only 
			#stakeAddr = "stake1u9vll54jq87vujs8dyek8jtv5cgen3406xe60eyw5hk64pslz0wzp"

			# search for assets
			assetCount = searchAddr(stakeAddr)

			# if no assets are found
			if assetCount == 0:
				print_log(str(username) + " Does not have a Cyclr NFT")
				await dm_user(user_id, "Could not find the required NFT in your wallet, try again later.", [], discord.Colour.red())
			else:
				member = guild.get_member(user_id)

				if member:
					role = discord.utils.get(guild.roles, name=ROLE_NAME)
					await member.add_roles(role)

					await insertMember(user_id, str(username), str(stakeAddr), str(txn), assetCount)
					print_log(str(member.name) + " has " + str(assetCount) + " tokens, " + str(ROLE_NAME) + " role given.")

					await dm_user(user_id, "You have been verified!",[["Asset Count: ",str(assetCount)],["Role Given",str(ROLE_NAME)]], discord.Colour.green())
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
		role = discord.utils.get(guild.roles, name=ROLE_NAME)

		member = guild.get_member(int(user['id']))
		if member:
			cur_cnt = int(user['ass_cnt'])
			if assetCount == 0:
				if ROLE_NAME.lower() in [x.name.lower() for x in member.roles]:
					await member.remove_roles(role)
				
				# remove record from DB
				await removeMember(user['id'])
				print_log(str(user['name']) + " has been removed from the club, address: " + str(user['addr']))
			elif assetCount != cur_cnt:
				print_log(str(user['name'] + " count has changed from " + str(cur_cnt) + " to " + str(assetCount)))
				await updateRoleResweep(user['id'], assetCount)
						

#################### END Resweep ####################



if __name__ == "__main__":
	init_discord_bot()
	mins = 0
	#print_log(str(time_remaining) + " until next resweep.")

	while True:
		if active:
			sleep(60)
			mins += 1
			if mins == 180:
				mins = 0
				discord_client.dispatch("resweep") #send this event to bot every half a day
			else:
				discord_client.dispatch("check_pending_tx") #send this event to bot every minute
			
			