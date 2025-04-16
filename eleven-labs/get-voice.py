import requests
import json

def get_voices():
    url = "https://api.elevenlabs.io/v1/voices"

    response = requests.request("GET", url)
    response_json = json.loads(response.text)
    print(json.dumps(response_json, indent=4))
    # print(response_json)

get_voices()