from pymongo import MongoClient
from pprint import pprint

from server_variables import *

client = MongoClient(port=27017)
# Check if address is currently being used
def searchPendingTx(addr):
	db = client.Cyclr.pendingTx
	if db.find_one({"addr":str(addr), "status": "waiting"}):
		return True
	return False

# check if stakeAddr exists
def findStakeAddr(addr):
	db = client.Cyclr.clubMembers
	if db.find_one({"addr":str(addr)}):
		return True
	return False

# find specific member
def findMember(user_id):
	db = client.Cyclr.clubMembers
	return db.find_one({"id": user_id},{"addr": 1})

# get all members 
def get_all_members():
	db = client.Cyclr.clubMembers
	members = []
	result = db.find({},{"addr":1,"id":1,"name":1, "ass_cnt": 1})
	for x in result:
		members.append({"id": str(x['id']),"addr": str(x['addr']),"name": str(x['name']),"ass_cnt": str(x['ass_cnt'])})
	return members

# check if user has a pending txn
def searchPendingUsr(uID):
	db = client.Cyclr.pendingTx
	result = db.find_one({"user_id": uID, "status": "waiting"},{"addr": 1, "attempts": 1, "amount": 1})
	if result:
		return result
	return None

# insert pending txn
async def insertPendingTx(mid,name,addr,amount):
	db = client.Cyclr.pendingTx
	pendingTx = {
	"user_id": int(mid),
	"username": str(name),
	"addr": str(addr),
	"amount": float(amount),
	"status": "waiting",
	"attempts": 0
	}
	db.insert_one(pendingTx)

# get all pending txn's
def getAllPendingAddr():
	db = client.Cyclr.pendingTx
	result = []
	result = db.find({"status": "waiting"},{"addr": 1, "username": 1, "user_id": 1, "amount": 1})
	return result

# check txn attempts and increase
async def checkAttempts(addr, amount):
	db = client.Cyclr.pendingTx
	r = db.find_one({"amount":amount, "addr": str(addr), "status": "waiting"},{"attempts": 1, "user_id": 1})
	if int(r['attempts'] >= TXN_TIME_LIMIT):
		newValues = { "$set": {"status": "expired"} }
		db.update_one({"addr": str(addr), "amount": amount, "status": "waiting"}, newValues)
		return r['user_id']
	else:
		newValues = { "$inc": {"attempts": 1} }
		db.update_one({"addr": str(addr), "amount": amount, "status": "waiting"}, newValues)
		return None

# insert refund into db
async def insertRefund(name, addr, amount):
	db = client.Cyclr.pendingRefunds
	refund = {
	"name": name,
	"addr": addr,
	"amount": float(amount),
	"status": "pending"
	}
	db.insert_one(refund)

# insert member to db
async def insertMember(mid,name,addr,txn, asset_cnt):
	db = client.Cyclr.clubMembers
	member = {
    "id": mid,
    "name": name,
    "ass_cnt": asset_cnt,
    "addr": addr,
    "txn": txn
	}
	db.insert_one(member)

# remove pending txn
def removePendingTx(addr):
	db = client.Cyclr.pendingTx
	newValues = { "$set": {"status": "payment_received"} }
	db.update_many({"addr": str(addr)}, newValues)

# remove member
async def removeMember(id):
	db = client.Cyclr.clubMembers
	db.delete_many({"id": int(id)})

async def removeMemberID(id):
	db = client.Cyclr.clubMembers
	db.delete_one({"id": int(id)})


# update member
async def updateRoleResweep(id, cnt):
	db = client.Cyclr.clubMembers

	newValues = { "$set": {"ass_cnt": cnt} }
	db.update_one({"id": int(id)}, newValues)

# remove txn
async def removeTx(mid):
	db = client.Cyclr.pendingTx
	db.delete_many({"user_id": int(mid), "status":"waiting"})