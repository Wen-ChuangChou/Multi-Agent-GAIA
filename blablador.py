import requests
import json


class Models():

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

    url = "https://helmholtz-blablador.fz-juelich.de:8000/v1/models"

    def get_model_data(self):
        response = requests.get(url=self.url, headers=self.headers)
        response = json.loads(response.text)
        return (response["data"])

    def get_model_ids(self):
        response = requests.get(url=self.url, headers=self.headers)
        response = json.loads(response.text)

        ids = []
        for model in response["data"]:
            ids.append(model["id"])

        return (ids)
