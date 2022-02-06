from helpers import MAGIC, POLICY_DIR, get_address, get_mint_address, get_slot_number
from build_and_sign_transaction import (OUT_DIR, REFUND_DIR, build_refund_transaction, 
    build_transaction, calculate_refund_transaction_fee, sign_refund_transaction, 
    sign_transaction, submit_transaction)
import time
import subprocess
import sys
import json

FEE = '100000000'
VALID_CHAINS = ['testnet-magic', 'mainnet']

"""
Creates a policy.script file.

Args:
    mintable_time: The time in slots that the policy will be open for.
    chain: The Cardano chain.

Returns:
    A boolean indicating whether the transaction was successful.
"""
def create_policy(mintable_time, chain='testnet-magic'):
    create_args = ['cardano-cli', 'address', 'key-gen', '--verification-key-file', 
        f'{POLICY_DIR}/policy.vkey', '--signing-key-file', f'{POLICY_DIR}/policy.skey']
    
    try:
        res = subprocess.run(create_args, capture_output=True).stderr.decode()

        if res:
            print(res)
            return False
    except subprocess.CalledProcessError:
        return False

    hash_args = ['cardano-cli', 'address', 'key-hash', '--payment-verification-key-file',
        f'{POLICY_DIR}/policy.vkey']

    try:
        res = subprocess.run(hash_args, capture_output=True)

        if res.stderr.decode():
            print(res.stderr.decode())
            return False
        
        key_hash = res.stdout.decode()
    except subprocess.CalledProcessError:
        return False
    
    slot_number = get_slot_number(chain)

    if slot_number:
        policy = {'type': 'all', 'scripts': [
            {'type': 'before', 'slot': slot_number+mintable_time},
            {'type': 'sig', 'keyHash': key_hash}
        ]}

        with open(f'{POLICY_DIR}/policy.script', 'w') as file:
            json.dump(policy, file)
        return True
    else:
        print('Error getting slot number...')
        return False

"""
Gets the transactions of the given address.

Args:
    address: The address to check transactions for.
    chain: The Cardano chain.

Returns:
    The unparsed transaction info in string format.
"""
def get_tx_info(address, chain='testnet-magic'):
    args = ['cardano-cli', 'query', 'utxo', '--address', address, f'--{chain}']

    if chain == 'testnet-magic':
        args.append(MAGIC)
    
    try:
        tx_info = subprocess.run(args, capture_output=True).stdout.decode()
    except subprocess.CalledProcessError:
        return False

    if tx_info:
        return tx_info
    else:
        return False

"""
Finds the next minting transaction.

Args:
    tx_info: The unparsed transaction info in string format.
    past_tx: The previous minting transaction.

Returns:
    The transaction hash (None if no new minting transactions) and tx_ix

Raises:
    IndexError: Raised when the tx_info is incorrectly formatted.
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
    tx_ix: The exclusive lower bound for which tx_ix's to monitor. 

Returns:
    The tx_ix of the last minting transaction or False if there was an error getting the address.
"""
def monitor(id, total_mint, chain='testnet-magic', tx_ix=-1):
    address = get_address()

    if not address:
        print('Error getting address...')
        return False

    while id <= total_mint:
        tx_info = get_tx_info(address, chain)

        if tx_info:
            try:
                tx_hash, tx_ix = find_next_transaction(tx_info, tx_ix)

                if tx_hash:
                    tx_response = get_mint_address(tx_hash, chain)

                    if 'error' not in tx_response:
                        mint_address = tx_response['inputs'][0]['address']

                        if build_transaction(tx_hash, tx_ix, mint_address, address, id, chain=chain):
                            if sign_transaction(id, chain):
                                if submit_transaction(f'{OUT_DIR}/matx{id}.signed', chain):
                                    id+=1
                                    continue
                                else:
                                    print('Error submitting mint transaction...')
                            else:
                                print('Error signing mint transaction...')
                        else:
                            print('Error building mint transaction...')
                    else:
                        print(tx_response['error'])
                else:
                    time.sleep(5)
                    continue
            except IndexError:
                print('Error when parsing transaction info...')
        else:
            print('Error when querying transaction info...')
        
        time.sleep(15)
    
    return tx_ix

"""
Monitors for late minters and refunds them.

Args:
    tx_ix: The last valid minting tx_ix.
    refund_time: The time in seconds to monitor for late minters.
    chain: The Cardano chain.

Returns:
    A boolean indicating whether the total refund time has been met.
"""
def refund_late_minters(tx_ix, refund_time=14400, chain='testnet-magic'):
    start = time.time()
    address = get_address()

    if not address:
        print('Error getting address...')
        return False

    while (time.time() - start) <= refund_time:
        tx_info = get_tx_info(address, chain)

        if tx_info:
            try:
                tx_hash, tx_ix = find_next_transaction(tx_info, tx_ix)

                if tx_hash:
                    tx_response = get_mint_address(tx_hash)

                    if 'error' not in tx_response:
                        mint_address = tx_response['inputs'][0]['address']
                        fee = calculate_refund_transaction_fee(tx_hash, tx_ix, mint_address,
                            FEE, chain)
                        
                        if fee:
                            if build_refund_transaction(tx_hash, tx_ix, mint_address, int(FEE) - int(fee)):
                                if sign_refund_transaction(tx_ix, chain):
                                    if submit_transaction(f'{REFUND_DIR}/tx{tx_ix}.signed', chain):
                                        continue
                                    else:
                                        print('Error submitting refund transaction...')
                                else:
                                    print('Error signing refund transaction...')
                            else:
                                print('Error building refund transaction...')
                        else:
                            print('Error calculating refund fee...')
                    else:
                        print(tx_response['error'])
                else:
                    time.sleep(5)
                    continue
            except IndexError:
                print('Error when parsing transaction info...')
        else:
            print('Error when querying transaction info...')

        time.sleep(15)

    return True
    
if __name__ == '__main__':
    chain = 'testnet-magic'
    refund_time = 14400
    new_policy = True

    for x in range(0,len(sys.argv)):
        if sys.argv[x] == '--starting-id':
            starting_id = sys.argv[x+1]
        elif sys.argv[x] == '--total-mint': 
            total_mint = sys.argv[x+1]
        elif sys.argv[x] == '--chain':
            chain = sys.argv[x+1]
        elif sys.argv[x] == '--refund-time':
            refund_time = sys.argv[x+1]
        elif sys.argv[x] == '--create-policy':
            if sys.argv[x+1].lower() == 'false':
                new_policy = False
        elif sys.argv[x] == '--mintable-time':
            mintable_time = int(sys.argv[x+1].strip())
            print(f'The policy will be open for {round(mintable_time/86400.0, 2)} days.')
    
    assert chain in VALID_CHAINS, f'Invalid argument for chain: {chain}'
    assert total_mint >= 1, f'Invalid argument for total mint: {total_mint}'
    assert refund_time >= 0, f'Invalid argument for refund time: {refund_time}'
    assert mintable_time > 0, f'Invalid argument for mintable time: {mintable_time}'
    
    if new_policy:
        policy_status = create_policy(mintable_time, chain)

    if not new_policy or policy_status:
        tx_ix = monitor(starting_id, total_mint, chain)

        if tx_ix:
            print('Minting has ended!')
            res = refund_late_minters(tx_ix, refund_time, chain)

            if res:
                print('Refunds have ended.')
    else:
        print('Error creating policy.script...')