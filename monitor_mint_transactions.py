from helpers import MAGIC, get_address, get_mint_address
from build_and_sign_transaction import OUT_DIR, build_raw_refund_transaction, build_transaction, sign_transaction
import time
import subprocess
import sys

FEE = '100000000'

def get_args(address, chain):
    args = ['cardano-cli', 'query', 'utxo', '--address', address, f'--{chain}']

    if chain == 'testnet-magic':
        args.append(MAGIC)
    
    return args

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

def monitor(id=1, total_mint=1000, chain='testnet-magic'):
    address = get_address()
    args = get_args(address, chain)
    
    tx_ix = -1

    while id <= total_mint:
        tx_info = subprocess.run(args, capture_output=True).stdout.decode()
        tx_hash, tx_ix = find_next_transaction(tx_info, tx_ix)

        if tx_hash:
            tx_response = get_mint_address(tx_hash)
            mint_address = tx_response['inputs'][0]['address']

            build_transaction(tx_hash, tx_ix, address, mint_address, id)
            sign_transaction(id)

            submit_args = ['cardano-cli', 'transaction', 'submit', '--tx-file', 
                f'{OUT_DIR}/matx{id}.signed', f'--{chain}']

            if chain == 'testnet-magic':
                args.append(MAGIC)

            subprocess.run(submit_args)
            id+=1
        else:
            time.sleep(5)
    
    return tx_ix

def refund_late_minters(tx_ix, refund_time=14400, chain='testnet-magic'):
    start = time.time()
    address = get_address()

    while (time.time() - start) <= refund_time:
        args = get_args(address, chain)
        tx_info = subprocess.run(args, capture_output=True).stdout.decode()
        tx_hash, tx_ix = find_next_transaction(tx_info, tx_ix)

        if tx_hash:
            tx_response = get_mint_address(tx_hash)
            mint_address = tx_response['inputs'][0]['address']
            build_raw_refund_transaction(tx_hash, tx_ix, mint_address, address, FEE, chain)
        else:
            time.sleep(5)
    
if __name__ == '__main__':
    tx_ix = monitor()
    refund_late_minters(tx_ix)