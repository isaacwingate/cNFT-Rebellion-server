from discord.ext import commands
import discord
from datetime import datetime

async def check_owner(ctx):
	is_owner = await ctx.bot.is_owner(ctx.author)
	if is_owner:
		return True
	else:
		return False

def is_owner():
    async def pred(ctx):              #ISAAC             
        return ctx.author.id in [339011064660492288]
    return commands.check(pred)

def is_admin_owner():
	async def pred(ctx):
		return ctx.author.id in [339011064660492288,586916122625048588,418107168818987008]
	return commands.check(pred)

def is_dm():
    async def pred(ctx):
        return isinstance(ctx.channel, discord.channel.DMChannel)
    return commands.check(pred)

async def dm_user(uid, msg):
	user = discord_client.get_user(int(uid))
	await user.send(str(msg))
	return

def print_log(log):
	now = datetime.now()
	current_time = now.strftime("%d/%m/%y %H:%M:%S")
	print(current_time + " - " + log)
	return

def binSearch(num, arr):
	low = 0
	high = len(arr) - 1

	while low <= high:
		middle = low + (high - low) // 2
		if arr[middle] == num:
			return True
		elif arr[middle] < num:
			low = middle + 1
		else:
			high = middle - 1
	return False