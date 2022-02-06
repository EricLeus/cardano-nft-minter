from helpers import MAGIC, get_address, get_mint_address
from build_and_sign_transaction import (OUT_DIR, REFUND_DIR, build_refund_transaction, 
    build_transaction, calculate_refund_transaction_fee, sign_refund_transaction, 
    sign_transaction, submit_transaction)
import time
import subprocess
import sys

FEE = '100000000'
VALID_CHAINS = ['testnet-magic', 'mainnet']

"""
Gets the transactions of the given address.

Args:
    address: The address to check transactions for.
    chain: The Cardano chain.

Returns:
    The unparsed transaction info in string format.

Raises:
    subprocess.CalledProcessError: Raised when the subprocess.run() function 
    returns a non-zero exit status
"""
def get_tx_info(address, chain='testnet-magic'):
    args = ['cardano-cli', 'query', 'utxo', '--address', address, f'--{chain}']

    if chain == 'testnet-magic':
        args.append(MAGIC)
    
    tx_info = subprocess.run(args, capture_output=True).stdout.decode()
    # Introduce error checking here
    return tx_info

"""
Finds the next minting transaction.

Args:
    tx_info: The unparsed transaction info in string format.
    past_tx: The previous minting transaction.

Returns:
    The transaction hash (None if no new minting transactions) and tx_ix
"""
def find_next_transaction(tx_info, past_tx):
    split_info = tx_info.split()
    for x in range(0,len(split_info)):
        if len(split_info[x]) == 64:
            tx_hash = split_info[x]
            tx_ix = int(split_info[x+1])

            if tx_ix > past_tx:
                amount = split_info[x+2]

                if amount == FEE:
                    return tx_hash, tx_ix

    return None, past_tx

"""
Monitors for minting transactions and executes them.

Args:
    id: The starting ID for the new NFTs.
    total_mint: The total number of new NFTs to mint.
    chain: The Cardano chain.

Returns:
    The tx_ix of the last minting transaction.
"""
def monitor(id, total_mint, chain='testnet-magic'):
    address = get_address()
    tx_ix = -1

    while id <= total_mint:
        tx_info = get_tx_info(address, chain)
        tx_hash, tx_ix = find_next_transaction(tx_info, tx_ix)

        if tx_hash:
            tx_response = get_mint_address(tx_hash)
            mint_address = tx_response['inputs'][0]['address']

            build_transaction(tx_hash, tx_ix, mint_address, address, id)
            sign_transaction(id)
            submit_transaction(f'{OUT_DIR}/matx{id}.signed', chain)
            id+=1
        else:
            time.sleep(5)
    
    return tx_ix

"""
Monitors for late minters and refunds them.

Args:
    tx_ix: The last valid minting tx_ix.
    refund_time: The time in seconds to monitor for late minters.
    chain: The Cardano chain.

Returns:
    True when refund_time has been reached.
"""
def refund_late_minters(tx_ix, refund_time=14400, chain='testnet-magic'):
    start = time.time()
    address = get_address()

    while (time.time() - start) <= refund_time:
        tx_info = get_tx_info(address, chain)
        tx_hash, tx_ix = find_next_transaction(tx_info, tx_ix)

        if tx_hash:
            tx_response = get_mint_address(tx_hash)
            mint_address = tx_response['inputs'][0]['address']
            fee = calculate_refund_transaction_fee(tx_hash, tx_ix, mint_address,
                address, FEE, chain)
            build_refund_transaction(tx_hash, tx_ix, mint_address, 
                int(FEE) - int(fee), chain)
            sign_refund_transaction(tx_ix, chain)
            submit_transaction(f'{REFUND_DIR}/tx{tx_ix}.signed', chain)
        else:
            time.sleep(5)

    return True
    
if __name__ == '__main__':
    chain = 'testnet-magic'
    refund_time = 14400

    for x in range(0,len(sys.argv)):
        if sys.argv[x] == '--starting-id':
            starting_id = sys.argv[x+1]
        elif sys.argv[x] == '--total-mint': 
            total_mint = sys.argv[x+1]
        elif sys.argv[x] == '--chain':
            chain = sys.argv[x+1]
        elif sys.argv[x] == '--refund-time':
            refund_time = sys.argv[x+1]
    
    assert chain in VALID_CHAINS, f'Invalid argument for chain: {chain}'
    assert total_mint >= 1, f'Invalid argument for total mint: {total_mint}'
    assert refund_time >= 0, f'Invalid argument for refund time: {refund_time}'
  
    tx_ix = monitor(starting_id, total_mint, chain)
    refund_late_minters(tx_ix, refund_time, chain)