import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID_JYP = os.environ.get("ELEVENLABS_VOICE_ID_JYP")

CHUNK_SIZE = 1024
voice_id = ELEVENLABS_VOICE_ID_JYP
url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

headers = {
  "Accept": "audio/mpeg",
  "Content-Type": "application/json",
  "xi-api-key": ELEVENLABS_API_KEY
}

data = {
  "text": "안녕하세요, 저는 제이와이피 주니어입니다.", # 
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
        "similarity_boost": 1, # 비슷한 정도? 0~1 사이
        "stability": 1, # 버라이어티와 반대척도? 낮을수록 버라이어티가 높아짐
        "style": 1, # 샘플과 비슷한 말투, 올릴수록 역시 안정성 떨어짐
        "use_speaker_boost": True
  }
}


now = datetime.now()
current_time = now.strftime("%Y-%m-%d_%H-%M-%S")

response = requests.post(url, json=data, headers=headers)
with open(f"./audio/output-{current_time}.mp3", 'wb') as f:
    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
        if chunk:
            f.write(chunk)
