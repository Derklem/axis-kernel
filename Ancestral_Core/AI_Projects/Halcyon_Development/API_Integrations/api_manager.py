import requests

def call_api(endpoint, data):
    response = requests.post(endpoint, json=data)
    return response.json()
