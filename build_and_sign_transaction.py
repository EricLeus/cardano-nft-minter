from generate_metadata import METADATA_DIR, generate_metadata
from helpers import POLICY_DIR, MAGIC, get_slot_number, get_policy_id
import subprocess

OUT_DIR = './matx'
REFUND_DIR = './refund'
SLOT_MARGIN = 10000

"""
Builds the minting transaction.

Args:
    tx_hash: The input transaction hash.
    tx_ix: The input tx_ix.
    addr_in: The address which requested the mint.
    addr_out: The address to send the change to.
    id: The ID of the NFT.
    output: The accompanying ADA (in Lovelace) sent with the NFT to meet UTxO requirement.
    chain: The Cardano chain.

Returns:
    A boolean indicating whether the transaction was successful.
"""
def build_transaction(tx_hash, tx_ix, addr_in, addr_out, id ,output='1400000', chain='testnet-magic'):
    args = ['cardano-cli', 'transaction', 'build', f'--{chain}']

    if chain == 'testnet-magic':
        args.append(MAGIC)

    args.append('--alonzo-era')
    args.append('--tx-in')
    args.append(f'{tx_hash}#{tx_ix}')
    args.append('--tx-out')

    metadata = generate_metadata(id)

    if not metadata:
        print('Error getting metadata...')
        return False
        
    policy_id = get_policy_id()

    if policy_id:
        token_name = list(metadata['721'][policy_id].keys())[0].encode('utf-8').hex()
        args.append(f'{addr_in}+{output}+1 {policy_id}.{token_name}')
        args.append('--change-address')
        args.append(addr_out)
        args.append(f'--mint=1 {policy_id}.{token_name}')
        args.append('--minting-script-file')
        args.append(f'{POLICY_DIR}/policy.script')
        args.append('--metadata-json-file')
        args.append(f'{METADATA_DIR}/metadata{id}.json')
        args.append('--invalid-hereafter')

        slot_number = get_slot_number(chain)

        if slot_number:
            args.append(f'{slot_number+SLOT_MARGIN}')

            args.append('--witness-override')
            args.append('2')
            args.append('--out-file')
            args.append(f'{OUT_DIR}/matx{id}.raw')
            
            try:
                res = subprocess.run(args, capture_output=True)

                if res.stderr.decode():
                    print(res.stderr.decode())
                    return False
            except subprocess.CalledProcessError:
                return False

            res_split = res.stdout.decode().split(':')

            if res_split[0] == 'Minimum required UTxO':
                output = res_split[1].split()[1]
                return build_transaction(tx_hash, tx_ix, addr_in, addr_out, id, output, chain)
            elif res_split[0] == 'Estimated transaction fee':
                return True
        else:
            print('Error when getting slot number...')
    else:
        print('Error when getting policy ID...')
    
    return False

"""
Signs the minting transaction.

Args:
    id: The NFT ID.
    chain: The Cardano chain.

Returns:
    A boolean indicating whether the transaction was successful.
"""
def sign_transaction(id, chain='testnet-magic'):
    args = ['cardano-cli', 'transaction', 'sign', '--signing-key-file', 'payment.skey', 
        '--signing-key-file', f'{POLICY_DIR}/policy.skey', f'--{chain}']
    
    if chain == 'testnet-magic':
        args.append(MAGIC)
    
    args.append('--tx-body-file')
    args.append(f'{OUT_DIR}/matx{id}.raw')
    args.append('--out-file')
    args.append(f'{OUT_DIR}/matx{id}.signed')
    
    try:
        res = subprocess.run(args, capture_output=True).stderr.decode()

        if res:
            print(res)
            return False

        return True
    except subprocess.CalledProcessError:
        return False

"""
Submits a transaction to the Cardano blockchain.

Args:
    tx_file_path: The filepath for the transaction.
    chain: The Cardano chain.

Returns:
    A boolean indicating whether the transaction was successful.
"""
def submit_transaction(tx_file_path, chain='testnet-magic'):
    args = ['cardano-cli', 'transaction', 'submit', '--tx-file', 
        tx_file_path, f'--{chain}']

    if chain == 'testnet-magic':
        args.append(MAGIC)
    
    try:
        res = subprocess.run(args, capture_output=True)
        
        if res.stdout.decode().strip() == 'Transaction successfully submitted.':
            return True
        
        print(res.stderr.decode())
        return False
    except subprocess.CalledProcessError:
        return False

"""
Calculates the fee for a refund transaction.

Args:
    tx_hash: The input transaction hash.
    tx_ix: The input tx_ix.
    addr_in: The address which requested the mint.
    addr_out: The address to send the change to.
    output: The amount of ADA (in Lovelace) sent by the minter.
    chain: The Cardano chain.

Returns:
    The transaction fee in Lovelace or False if the calculation was not successful.
"""
def calculate_refund_transaction_fee(tx_hash, tx_ix, addr_in, output, chain='testnet-magic'):
    raw_args = ['cardano-cli', 'transaction', 'build-raw', '--tx-in', f'{tx_hash}#{tx_ix}',
        '--tx-out', f'{addr_in}+{output}', '--ttl', '0', '--fee', '0', '--out-file', 
        f'{REFUND_DIR}/tx{addr_in}.raw']
    
    try:
        raw_res = subprocess.run(raw_args, capture_output=True).stderr.decode()

        if raw_res:
            print(raw_res)
            return False
    except subprocess.CalledProcessError:
        return False

    fee_args = ['cardano-cli', 'transaction', 'calculate-min-fee', '--tx-body-file', 
        f'{REFUND_DIR}/tx{addr_in}.raw', '--tx-in-count', '1', '--tx-out-count', '1',
        '--witness-count', '1', '--byron-witness-count', '0', f'--{chain}']
    
    if chain == 'testnet-magic':
        fee_args.append(MAGIC)
    
    fee_args.append('--protocol-params-file')
    fee_args.append('protocol.json')
    
    try:
        fee_res = subprocess.run(fee_args, capture_output=True)

        if fee_res.stderr.decode():
            print(fee_res.stderr.decode())
            return False
        
        fee = fee_res.stdout.decode().split()[0]
        return fee
        
    except subprocess.CalledProcessError:
        return False

"""
Builds the refund transaction.

Args:
    tx_hash: The input transaction hash.
    tx_ix: The input tx_ix.
    addr_in: The address which requested the mint.
    output: The amount of ADA (in Lovelace) being refunded to the minter.
    fee: The transaction fee in Lovelace.
    chain: The Cardano chain.

Returns:
    A boolean indicating whether the transaction was successful.
"""
def build_refund_transaction(tx_hash, tx_ix, addr_in, output, fee, chain='testnet-magic'):
    slot_number = get_slot_number(chain)

    if not slot_number:
        print('Error getting slot number...')
        return False

    args = ['cardano-cli', 'transaction', 'build-raw', '--tx-in', f'{tx_hash}#{tx_ix}', 
        '--tx-out', f'{addr_in}+{output}', '--ttl', f'{slot_number+SLOT_MARGIN}', 
        '--fee', fee, '--out-file', f'{REFUND_DIR}/tx{addr_in}.raw']
    
    try:
        res = subprocess.run(args, capture_output=True).stderr.decode()

        if res:
            print(res)
            return False
        
        return True
    except subprocess.CalledProcessError:
        return False

"""
Signs the refund transaction.

Args:
    tx_ix: The input tx_ix.
    addr_in: The address which requested to mint.
    chain: The Cardano chain.

Returns:
    A boolean indicating whether the transaction was successful.
"""
def sign_refund_transaction(tx_ix, addr_in, chain='testnet-magic'):
    args = ['cardano-cli', 'transaction', 'sign', '--tx-body-file', 
        f'{REFUND_DIR}/tx{addr_in}.raw', '--signing-key-file', 'payment.skey',
        f'--{chain}']

    if chain == 'testnet-magic':
        args.append(MAGIC)
    
    args.append('--out-file')
    args.append(f'{REFUND_DIR}/tx{addr_in}.signed')
    
    try:
        res = subprocess.run(args, capture_output=True).stderr.decode()

        if res:
            print(res)
            return False

        return True
    except subprocess.CalledProcessError:
        return False