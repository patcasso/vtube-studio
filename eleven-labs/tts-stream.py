import os
import requests
from dotenv import load_dotenv

load_dotenv()
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID_JYP = os.environ.get("ELEVENLABS_VOICE_ID_JYP")

voice_id = ELEVENLABS_VOICE_ID_JYP
url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

querystring = {"optimize_streaming_latency": "2", "output_format": "mp3_44100_64"}

payload = {
    "model_id": "eleven_multilingual_v2",
    "text": "Hello, this is JYP Junior.",
    "voice_settings": {
        "similarity_boost": 1,
        "stability": 1,
        "style": 1,
        "use_speaker_boost": True,
    },
}
headers = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json",
}

response = requests.request(
    "POST", url, json=payload, headers=headers, params=querystring
)

# print(response.text)
print(response)
