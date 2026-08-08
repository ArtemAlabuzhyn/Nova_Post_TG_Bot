import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NOVA_POST_API_KEY")
API_URL = "https://api.novaposhta.ua/v2.0/json/"


payload = {

    'apiKey': api_key,
    'modelName': "AddressGeneral",
    'calledMethod': 'searchSettlements',
    'methodProperties': {
        'CityName': 'Київ',
        'Limit': 5}
}

response = requests.post(
    API_URL,
    json=payload,
    timeout=10
)

result = response.json()
print('success', result.get('success'))
print('errors', result.get('errors'))
print('Count of results', len(result.get('data', [])))
addresses = result['data'][0]['Addresses']

for address in addresses:
    print(f'{address['Present']} - отделений: {address["Warehouses"]}')



