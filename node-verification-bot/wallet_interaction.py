
# Init queue of payment addresses
def initQueue():
    queue = []
    wal = Wallet(WALLET_ID, backend=WalletREST(port=1338))

    allAddresses = wal.addresses(with_usage=True)

    for addr, used in allAddresses:
        if not used and not searchPendingTx(addr):
            queue.append(addr)

    print("Free addr's: ", len(queue))
    return queue