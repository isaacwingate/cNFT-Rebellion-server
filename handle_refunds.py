import requests
from cardano.wallet import Wallet
from cardano.backends.walletrest import WalletREST
from pymongo import MongoClient
from datetime import datetime
from time import sleep

from server_variables import *

client = MongoClient(port=27017)
db = client.Kong.pendingRefunds

wal = Wallet(WALLET_ID, backend=WalletREST(port=1338))

def print_log(log):
	now = datetime.now()
	current_time = now.strftime("%d/%m/%y %H:%M:%S")
	print(current_time + " - " + log)
	return

LIMIT = 5
consecutive_count = 0

while(True):
	cnt = db.count()
	if cnt >= LIMIT:

		batch = list(db.find().limit(LIMIT))
		txes =  tuple((b['addr'], b['amount']) for b in batch)
		txn = wal.transfer_multiple(txes, passphrase="&3$5(Pi)5$3&",)

		for b in batch:
			db.delete_one({"_id": b['_id']})
		print_log("refunds sent, txn: " + str(txn))

		sleep(60)
		consecutive_count = 0
		
	elif consecutive_count == 10 and cnt >= 1:

		print_log(str(cnt) + " refunds waiting too long, refunding now")
		batch = list(db.find().limit(cnt))
		txes =  tuple((b['addr'], b['amount']) for b in batch)
		txn = wal.transfer_multiple(txes, passphrase="&3$5(Pi)5$3&",)

		for b in batch:
			db.delete_one({"_id": b['_id']})

		print_log("refunds sent, txn: " + str(txn))

		sleep(60)
		consecutive_count = 0

	elif cnt == 0:
		print_log("No pending refunds, consec_count: " + str(consecutive_count))
		consecutive_count = 0
		sleep(120)

	else:
		print_log("not enough pending refunds, count: " + str(cnt))
		consecutive_count += 1
		sleep(120)


