from pymongo import MongoClient
from pprint import pprint


client = MongoClient(port=27017)

def searchPendingTx(addr):
	db = client.AdaApocalypse.pendingTx
	if db.find_one({"addr":str(addr), "status": "waiting"}):
		return True
	return False

async def get_all_addr():
	db = client.AdaApocalypse.clubMembers
	addresses = []
	result = db.find({},{"addr":1,"id":1,"name":1, "role": 1, "ass_cnt": 1})
	for x in result:
		addresses.append({"id": str(x['id']),"addr": str(x['addr']),"name": str(x['name']),"role": str(x['role']),"ass_cnt": str(x['ass_cnt'])})
	return addresses
