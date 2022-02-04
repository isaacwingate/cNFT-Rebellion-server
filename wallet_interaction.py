import requests
from cardano.wallet import Wallet
from cardano.backends.walletrest import WalletREST

import pprint
pp = pprint.PrettyPrinter(indent=4).pprint

from server_variables import *
from helper_funcs import print_log, binSearch
from handle_db import *

# Init queue of payment addresses
def initQueue():
	queue = []
	wal = Wallet(WALLET_ID, backend=WalletREST(port=1338))

	allAddresses = wal.addresses(with_usage=True)

	for addr in allAddresses:
		if not addr[1] and not searchPendingTx(str(addr[0])):
			queue.append(addr[0])

	print("Free addr's: ", len(queue))
	return queue

# check if payment has been received
def checkForPayment(paymentAddr, amount):
	payment_url = "https://cardano-mainnet.blockfrost.io/api/v0/addresses/"+str(paymentAddr)+"/total"
	auth = {'project_id' : BLOCKFROST_KEY}

	payment_response = requests.get(payment_url,headers=auth)

	if not payment_response:
		return None,None


	if float(payment_response.json()['received_sum'][0]['quantity']) == int(amount * 1000000):
		print_log(str(amount) + ' payment received on ' + str(paymentAddr))

		txn_url = "https://cardano-mainnet.blockfrost.io/api/v0/addresses/"+str(paymentAddr)+"/txs?order=desc"
		txn_response = requests.get(txn_url,headers=auth)

		#pp(txn_response.json())

		correct_txn = ""

		for txn in txn_response.json():
			utxo_url = "https://cardano-mainnet.blockfrost.io/api/v0/txs/"+str(txn)+"/utxos"
			utxo_response = requests.get(utxo_url,headers=auth)

			payment_quantity = int(utxo_response.json()['outputs'][0]['amount'][0]['quantity'])

			if payment_quantity == int(amount * 1000000):
				addr = utxo_response.json()['outputs'][1]['address']
				correct_txn = txn
				# remove pending txn
				removePendingTx(paymentAddr)
				return addr, correct_txn
			

	return None, None

# get stake address from addr
def getStakeAddr(userAddr):
	api_url = "https://cardano-mainnet.blockfrost.io/api/v0/addresses/"+str(userAddr)
	auth = {'project_id' : BLOCKFROST_KEY}
	response = requests.get(api_url,headers=auth)
	if response.json():
		return response.json()['stake_address']
	return None

# search wallet for assets
def searchAddr(addr):
	api_url = "https://cardano-mainnet.blockfrost.io/api/v0/accounts/"+str(addr)+"/addresses/assets"
	auth = {'project_id' : BLOCKFROST_KEY}
	cnt = 0

	page = 1
	while(True):
		param = {'page' : page}
		response = requests.get(api_url,headers=auth, params=param)
		if response.json():
			for x in response.json():
				for p in POLICY:
					asset_id = str(x['unit'])
					if asset_id.startswith(p):
						cnt += 1

						
			page +=1
		else:
			return cnt

