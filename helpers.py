from dotenv import load_dotenv
import os
import requests
import subprocess
import json

load_dotenv()

MAGIC = '1097911063'

API_URL = 'https://ipfs.blockfrost.io/api/v0/'
ADD_ENDPOINT = 'ipfs/add/'
PIN_ENDPOINT = 'ipfs/pin/add/'
TRANSACTION_ENDPOINT = 'txs/{}/utxos'

ADDRESS_DIR = './payment.addr'
POLICY_DIR = './policy'

"""
Gets the policy ID.

Returns:
    The policy ID or False if the policy ID was not found.
"""
def get_policy_id():
    try:
        with open(f'{POLICY_DIR}/policyID', 'r') as file:
            policy_id = file.readline().strip()
        return policy_id
    except FileNotFoundError:
        return False

"""
Adds the given image to IPFS.

Args:
    img: The image to add.

Returns:
    The response of the Blockfrost API.
"""
def add_image_to_ipfs(img):
    response = requests.post(
        API_URL + ADD_ENDPOINT, 
        headers={'project_id':os.getenv('PROJECT_ID')},
        files={'file':img}
    ).json()
    return response

"""
Pins the given hash to IPFS.

Args:
    hash: The hash to pin.

Returns:
    The response of the Blockfrost API.
"""
def pin_image_to_ipfs(hash):
    response = requests.post(
        API_URL + PIN_ENDPOINT + hash, 
        headers={'project_id':os.getenv('PROJECT_ID')}
    ).json()
    return response

"""
Gets the transaction information.

Args:
    tx_hash: The transaction hash.

Returns:
    The response of the Blockfrost API.
"""
def get_mint_address(tx_hash, chain='testnet-magic'):
    response = requests.get(
        API_URL + TRANSACTION_ENDPOINT.format(tx_hash), 
        headers={'project_id':os.getenv('PROJECT_ID')}
    ).json()
    return response

"""
Gets the local stored Cardano address.

Returns:
    The address or False if the address is not found.
"""
def get_address():
    try:
        with open(ADDRESS_DIR, 'r') as file:
            address = file.readline().strip()
        return address
    except FileNotFoundError:
        return False

"""
Gets the current slot number of the Cardano chain.

Args:
    chain: The Cardano chain.

Returns:
    The current slot number.
"""
def get_slot_number(chain):
    args = ['cardano-cli', 'query', 'tip', f'--{chain}']

    if chain == 'testnet-magic':
        args.append(MAGIC)

    try:
        output = subprocess.run(args, capture_output=True).stdout.decode()
    except subprocess.CalledProcessError:
        return False

    try:
        slot_number = json.loads(output)['slot']
        return slot_number
    except KeyError:
        return False