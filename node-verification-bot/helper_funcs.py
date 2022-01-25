async def check_owner(ctx):
	is_owner = await ctx.bot.is_owner(ctx.author)
	if is_owner:
		return True
	else:
		return False

def is_owner():
    async def pred(ctx):              #ISAAC             #MOC
        return ctx.author.id in [339011064660492288, 455132283821883402]
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