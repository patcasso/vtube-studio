import os
import pygame
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(
    api_key=OPENAI_API_KEY,
)

# audio 파일이 생성될 폴더 만들기
directory_path = "./audio"
os.makedirs(directory_path, exist_ok=True)

def create_tts(input):
    # input = "만나서 반가워요. 좋은 아침이에요."

    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=input,
    )

    response.stream_to_file("./audio/output.mp3")


def play_tts(filename): # 음성 재생 
    # Initialize the pygame mixer
    pygame.mixer.init()

    # Load a sound file
    sound_file = f"./{filename}"
    sound = pygame.mixer.Sound(sound_file)

    # Play the sound
    sound.play()

    # Wait for the sound to finish playing
    pygame.time.wait(int(sound.get_length() * 1000))
