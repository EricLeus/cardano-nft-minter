from generate_metadata import METADATA_DIR, generate_metadata
from helpers import POLICY_DIR, MAGIC, get_policy_id
import subprocess
import json

OUT_DIR = './matx'
REFUND_DIR = './refund'
SLOT_MARGIN = 10000

def get_slot_number(chain):
    args = ['cardano-cli', 'query', 'tip', f'--{chain}']

    if chain == 'testnet-magic':
        args.append(MAGIC)

    output = subprocess.run(args, capture_output=True).stdout.decode()
    slot_number = json.loads(output)['slot']
    return slot_number

def build_transaction(tx_hash, tx_ix, addr_in, addr_out, id, output='1400000', chain='testnet-magic'):
    args = ['cardano-cli', 'transaction', 'build', f'--{chain}']

    if chain == 'testnet-magic':
        args.append(MAGIC)

    args.append('--many-era')
    args.append('--tx-in')
    args.append(f'{tx_hash}#{tx_ix}')
    args.append('--tx-out')

    metadata = generate_metadata(id)
    policy_id = get_policy_id()
    token_name = list(metadata['721'][policy_id].keys())[0].encode('utf-8').hex()

    args.append(f'{addr_out}+{output}+"1 {policy_id}.{token_name}"')
    args.append('--change-address')
    args.append(addr_in)
    args.append(f'--mint="1 {policy_id}.{token_name}"')
    args.append('--minting-script-file')
    args.append(f'{POLICY_DIR}/policy.script')
    args.append('--metadata-json-file')
    args.append(f'{METADATA_DIR}/metadata{id}.json')
    args.append('--invalid-hereafter')

    slot_number = get_slot_number()
    args.append(f'{slot_number+SLOT_MARGIN}')

    args.append('--witness-override')
    args.append('2')
    args.append('--out-file')
    args.append(f'{OUT_DIR}/matx{id}.raw')

    res = subprocess.run(args, capture_output=True).stdout.decode()
    res_split = res.split(':')

    if res_split[0] == 'Minimum required UTxO':
        output = res_split[1].split()[1]
        return build_transaction(tx_hash, tx_ix, addr_in, addr_out, id, output, chain)
    elif res_split[0] == 'Estimated transaction fee':
        return True
    
    return False

def sign_transaction(id, chain='testnet-magic'):
    args = ['cardano-cli', 'transaction', 'sign', '--signing-key-file', 'payment.skey', 
        '--signing-key-file', f'{POLICY_DIR}/policy.skey', f'--{chain}']
    
    if chain == 'testnet-magic':
        args.append(MAGIC)
    
    args.append('--tx-body-file')
    args.append(f'{OUT_DIR}/matx{id}.raw')
    args.append('--out-file')
    args.append(f'{OUT_DIR}/matx{id}.signed')

    subprocess.run(args)
    return True

def build_raw_refund_transaction(tx_hash, tx_ix, addr_in, addr_out, output, chain='testnet-magic'):
    raw_args = ['cardano-cli', 'transaction', 'build-raw', '--tx-in', f'{tx_hash}#{tx_ix}',
        '--tx-out', f'{addr_out}+{output}', '--tx-out', f'{addr_in}+0', '--ttl', '0', 
        '--fee', '0', '--out-file', f'{REFUND_DIR}/tx{tx_ix}.raw']
    subprocess.run(raw_args)

    fee_args = ['cardano-cli', 'transaction', 'calculate-min-fee', '--tx-body-file', 
        f'{REFUND_DIR}/tx{tx_ix}.raw', '--tx-in-count', '1', '--tx-out-count', '2',
        '--witness-count', '1', '--byron-witness-count', '0', f'--{chain}']
    
    if chain == 'testnet-magic':
        fee_args.append(MAGIC)
    
    fee_args.append('--protocol-params-file')
    fee_args.append('protocol.json')

    res = subprocess.run(fee_args, capture_output=True).stdout.decode()
    fee = res.split()[0]

    



    