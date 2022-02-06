from dotenv import load_dotenv
import os
import requests

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
    The policy ID.

Raises:
    FileNotFoundError: Raised when the policyID file is not found.
"""
def get_policy_id():
    with open(f'{POLICY_DIR}/policyID', 'r') as file:
        policy_id = file.readline().strip()
    return policy_id

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
def get_mint_address(tx_hash):
    response = requests.get(
        API_URL + TRANSACTION_ENDPOINT.format(tx_hash), 
        headers={'project_id':os.getenv('PROJECT_ID')}
    ).json()
    return response

"""
Gets the local stored Cardano address.

Returns:
    The address.

Raises:
    FileNotFoundError: Raised when the address file is not found.
"""
def get_address():
    with open(ADDRESS_DIR, 'r') as file:
        address = file.readline().strip()
    return address