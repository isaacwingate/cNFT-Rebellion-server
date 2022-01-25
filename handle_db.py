from pymongo import MongoClient
from pprint import pprint

from server_variables import *

client = MongoClient(port=27017)
# Check if address is currently being used
def searchPendingTx(addr):
	db = client.AdaApocalypse.pendingTx
	if db.find_one({"addr":str(addr), "status": "waiting"}):
		return True
	return False

# find specific member
def findMember(user_id):
	db = client.AdaApocalypse.clubMembers
	return db.find_one({"id": user_id},{"addr": 1})

# get all members 
def get_all_members():
	db = client.AdaApocalypse.clubMembers
	members = []
	result = db.find({},{"addr":1,"id":1,"name":1, "role": 1, "ass_cnt": 1})
	for x in result:
		members.append({"id": str(x['id']),"addr": str(x['addr']),"name": str(x['name']),"role": str(x['role']),"ass_cnt": str(x['ass_cnt'])})
	return members

# check if user has a pending txn
def searchPendingUsr(uID):
	db = client.AdaApocalypse.pendingTx
	result = db.find_one({"user_id": uID, "status": "waiting"},{"addr": 1, "attempts": 1, "amount": 1})
	if result:
		return result
	return None

# insert pending txn
async def insertPendingTx(mid,name,addr,amount):
	db = client.AdaApocalypse.pendingTx
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
	db = client.AdaApocalypse.pendingTx
	result = []
	result = db.find({"status": "waiting"},{"addr": 1, "username": 1, "user_id": 1, "amount": 1})
	return result

# check txn attempts and increase
def checkAttempts(addr):
	db = client.AdaApocalypse.pendingTx
	result = db.find_one({"addr": addr, "status": "waiting"},{"attempts": 1, "user_id": 1})
	if int(result['attempts'] >= TXN_TIME_LIMIT):
		newValues = { "$set": {"status": "expired"} }
		db.update_one({"addr": str(addr)}, newValues)
		return result['user_id']
	else:
		newValues = { "$inc": {"attempts": 1} }
		db.update_one({"addr": str(addr)}, newValues)
		return None

# insert refund into db
async def insertRefund(name, addr, amount):
	db = client.AdaApocalypse.pendingRefunds
	refund = {
	"name": name,
	"addr": addr,
	"amount": float(amount),
	"status": "pending"
	}
	db.insert_one(refund)

# insert member to db
async def insertMember(mid,name,addr,txn, role_name, asset_cnt):
	db = client.AdaApocalypse.clubMembers
	member = {
    "id": mid,
    "name": name,
    "role": role_name,
    "ass_cnt": asset_cnt,
    "addr": addr,
    "txn": txn
	}
	db.insert_one(member)

# remove pending txn
def removePendingTx(addr):
	db = client.AdaApocalypse.pendingTx
	newValues = { "$set": {"status": "payment_received"} }
	db.update_many({"addr": str(addr)}, newValues)

# remove member
async def removeMember(addr):
	db = client.AdaApocalypse.clubMembers
	db.delete_one({"addr": str(addr)})

# update member
async def updateRoleResweep(id, role, cnt):
	db = client.AdaApocalypse.clubMembers

	newValues = { "$set": {"role": str(role), "ass_cnt": cnt} }
	db.update_one({"id": int(id)}, newValues)