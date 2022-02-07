from monitor_mint_transactions import TEST_ADDRESSES, FEE, get_address
from helpers import get_slot_number
import subprocess

# Add automatic test address generation

# Update manually
TX_HASHES = [
    '7bc3bd843e9b3a1a5caba99c04819e5dec18778053754fc57b2fa64ec64a65a3',
    '7b7143584c310fa3e70b39ec9761ed3f8ffc79010d818ab86075de8a24b6573f',
    '7bc3bd843e9b3a1a5caba99c04819e5dec18778053754fc57b2fa64ec64a65a3']
TX_IXS = [1, 0, 0]
FUNDS = [780000000, 109825215, 109825215]

def submit_mint_request(index):
    address = get_address()
    args = ['cardano-cli', 'transaction', 'build-raw', '--tx-in', f'{TX_HASHES[index]}#{TX_IXS[index]}',
        '--tx-out', f'{address}+{FEE}', '--tx-out', f'{TEST_ADDRESSES[index]}+{FUNDS[index]-int(FEE)}',
        '--ttl', '0', '--fee', '0', '--out-file', 'tx.raw']
    subprocess.run(args)

    args = ['cardano-cli', 'transaction', 'calculate-min-fee', '--tx-body-file', 
        'tx.raw', '--tx-in-count', '1', '--tx-out-count', '2', '--witness-count', 
        '1', '--byron-witness-count', '0', '--testnet-magic', '1097911063',
        '--protocol-params-file', 'protocol.json']
    
    fee = int(subprocess.run(args, capture_output=True).stdout.decode().split()[0])

    args = ['cardano-cli', 'transaction', 'build-raw', '--tx-in', f'{TX_HASHES[index]}#{TX_IXS[index]}',
        '--tx-out', f'{address}+{FEE}', '--tx-out', f'{TEST_ADDRESSES[index]}+{FUNDS[index]-int(FEE)-fee}',
        '--ttl', str(get_slot_number()+10000), '--fee', str(fee), '--out-file', 'tx.raw']
    
    subprocess.run(args)

    args = ['cardano-cli', 'transaction', 'sign', '--tx-body-file', 
        'tx.raw', '--signing-key-file', f'payment{index+1}.skey',
        '--testnet-magic', '1097911063', '--out-file', 'tx.signed']
    
    subprocess.run(args)

    args = ['cardano-cli', 'transaction', 'submit', '--tx-file', 
        'tx.signed', '--testnet-magic', '1097911063']
    
    subprocess.run(args)

submit_mint_request(0)
submit_mint_request(1)
submit_mint_request(2)