from helpers import add_image_to_ipfs, pin_image_to_ipfs, get_policy_id
import json
import secrets
import os

IMG_DIR = './img'
METADATA_DIR = './metadata'
HASHES_DIR = './hashes.json'
NAME = 'TokenFund'
DESCRIPTION = 'Receives monthly dividends from the Token Fund'
TYPE = 'Angel'

"""
Generates the metadata for an NFT.

Args:
    id: The ID of the NFT.

Returns:
    The metadata of the NFT in JSON format or False if an error occured.
"""
def generate_metadata(id):
    policy_id = get_policy_id()

    if not policy_id:
        print('Error getting policy ID...')
        return False

    metadata = {'721': {policy_id: {}}}
    images = os.listdir(IMG_DIR)
    image = images[secrets.randbelow(len(images))]

    try:
        with open(HASHES_DIR, 'r') as file:
            image_hashes = json.load(file)
    except FileNotFoundError:
        image_hashes = dict()

    if image not in image_hashes:
        add_response = add_image_to_ipfs(open(f'{IMG_DIR}/{image}', 'rb'))
        hash = add_response['Hash']
        pin_response = pin_image_to_ipfs(hash)
    else:
        hash = image_hashes[image]

    if image in image_hashes or 'error' not in pin_response:
        name = f'{NAME}{str(id).zfill(5)}'
        metadata['721'][policy_id][name] = {
            'description': DESCRIPTION,
            'name': name,
            'id': id,
            'image': f'ipfs://{hash}',
            'type': TYPE
        }
        image_hashes[image] = hash

        with open(HASHES_DIR, 'w') as file:
            json.dump(image_hashes, file)
    
    with open(f'{METADATA_DIR}/metadata{id}.json', 'w') as file:
        json.dump(metadata, file)
    
    return metadata