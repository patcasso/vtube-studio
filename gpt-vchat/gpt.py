import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(
    api_key=OPENAI_API_KEY,
)

# system = "You are helpful AI."

def run_gpt(messages):
  response = client.chat.completions.create(
    model="gpt-4.1",  # 또는 다른 모델을 사용
    # messages=[
    #     {"role": "system", "content": system},
    #     {"role": "user", "content": user},
    # ],
    messages=messages
)
  response = response.json()
  response = json.loads(response)
  return response["choices"][0]["message"]['content']
