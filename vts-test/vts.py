import os
import asyncio
import websockets
import json
import time
import pygame
import librosa
import numpy as np
from dotenv import load_dotenv

load_dotenv()
VTUBE_STUDIO_AUTH_TOKEN = os.environ.get("VTUBE_STUDIO_AUTH_TOKEN")

audio_file_path = "./audio/output.mp3"
# Modified read_volume function to return both times and values
def read_volume(audio_file_path=audio_file_path):
    # Load the audio file
    y, sr = librosa.load(audio_file_path)
    
    # Calculate the root mean square (RMS) energy for each frame
    hop_length = 512  # Default hop length in librosa
    frame_length = 2048  # Default frame length
    
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    # Get the time for each frame
    times = librosa.times_like(rms, sr=sr, hop_length=hop_length)
    
    # Normalize the RMS values to a 0-100 range
    normalized_rms = np.interp(rms, (0, rms.max()), (0, 1))
    mouth_values = normalized_rms * 3
    
    return times, mouth_values

# Function to play audio and control mouth movement simultaneously
async def play_audio_with_mouth_sync(websocket, audio_path=audio_file_path):
    # 1. Analyze audio first to get timing and mouth values
    print("Analyzing audio...")
    times, mouth_values = read_volume(audio_path)
    
    # 2. Create custom parameter if needed
    creation_request = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": "ParamCreate_MouthOpenAmount",
        "messageType": "ParameterCreationRequest",
        "data": {
            "parameterName": "MouthOpenAmount",
            "explanation": "Controls the amount of mouth open from audio volume.",
            "min": 0,
            "max": 100,
            "defaultValue": 0,
        },
    }
    print("\n📌 Creating custom tracking parameter 'MouthOpenAmount'...")
    await send_api_request(creation_request, websocket)
    
    # 3. Prepare for synchronized playback
    print("Preparing for synchronized playback...")
    pygame.mixer.init()
    sound = pygame.mixer.Sound(audio_path)
    
    # 4. Set up timing variables
    frame_count = len(times)
    current_frame = 0
    
    # 5. Start audio playback
    print("Starting audio playback and mouth animation...")
    sound.play()
    start_time = time.time()
    
    # 6. Main synchronization loop
    while current_frame < frame_count:
        # Calculate what frame we should be on based on elapsed time
        elapsed_time = time.time() - start_time
        target_frame = 0
        
        # Find the appropriate frame for the current time
        while target_frame < frame_count and times[target_frame] < elapsed_time:
            target_frame += 1
            
        if target_frame >= frame_count:
            break
            
        # Only send updates when we move to a new frame
        if target_frame > current_frame:
            current_frame = target_frame
            mouth_value = mouth_values[current_frame]
            
            # Apply a scaling factor to make movements more pronounced
            # Adjust the multiplier (20) as needed for your character
            scaled_value = min(mouth_value * 20, 100)
            
            # Send the parameter to VTube Studio
            api_request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "MouthSync",
                "messageType": "InjectParameterDataRequest",
                "data": {
                    "faceFound": True,
                    "mode": "set",
                    "parameterValues": [
                        {"id": "MouthOpenAmount", "value": scaled_value},
                    ],
                },
            }
            await send_api_request(api_request, websocket, silent=True)
        
        # Small sleep to prevent flooding with requests
        await asyncio.sleep(0.01)
    
    # 7. Wait for audio to finish and reset mouth
    remaining_time = sound.get_length() - elapsed_time
    if remaining_time > 0:
        await asyncio.sleep(remaining_time)
    
    # 8. Reset mouth to closed position
    reset_request = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": "ResetMouth",
        "messageType": "InjectParameterDataRequest",
        "data": {
            "faceFound": True,
            "mode": "set",
            "parameterValues": [
                {"id": "MouthOpenAmount", "value": 0},
            ],
        },
    }
    await send_api_request(reset_request, websocket)
    print("Audio playback and mouth animation completed.")

# Silent version of send_api_request for high-frequency updates
async def send_api_request(request, websocket, silent=False):
    api_request_json = json.dumps(request)
    await websocket.send(api_request_json)
    response = await websocket.recv()
    if not silent:
        response_json = json.loads(response)
        print(json.dumps(response_json, indent=4))
        return response_json
    return json.loads(response)

# Your existing functions
async def request_auth_token(websocket):
    token_request = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": "TokenRequestID",
        "messageType": "AuthenticationTokenRequest",
        "data": {
            "pluginName": "VtsTestPlugin",
            "pluginDeveloper": "Patcasso",
        },
    }
    print("\n🔑 Requesting authentication token...")
    response = await send_api_request(token_request, websocket)

    if response["messageType"] == "AuthenticationTokenResponse":
        token = response["data"]["authenticationToken"]
        print(f"\n✅ Token received: {token}")
        return token
    elif response["messageType"] == "APIError":
        print(f"\n❌ Error: {response['data']['message']}")
        return None
    else:
        print("\n❌ Unexpected response.")
        return None

async def authenticate_with_token(websocket, token):
    auth_request = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": "AuthRequestID",
        "messageType": "AuthenticationRequest",
        "data": {
            "pluginName": "VtsTestPlugin",
            "pluginDeveloper": "Patcasso",
            "authenticationToken": token,
        },
    }
    print("\n🔐 Authenticating with token...")
    response = await send_api_request(auth_request, websocket)

    if (
        response["messageType"] == "AuthenticationResponse"
        and response["data"]["authenticated"]
    ):
        print("\n✅ Plugin authenticated!")
        return True
    else:
        print("\n❌ Authentication failed.")
        return False

# Modified main function
async def main():
    uri = "ws://localhost:8001"

    async with websockets.connect(uri) as websocket:
        print("1. 입력된 토큰 사용")
        print("2. 새로 토큰 요청 (팝업 뜸)")
        token_option = input("선택 (1/2): ")

        token = None
        if token_option == "1":
            # token = input("저장된 토큰 입력: ")
            token = VTUBE_STUDIO_AUTH_TOKEN
        elif token_option == "2":
            token = await request_auth_token(websocket)
        else:
            print("잘못된 입력.")
            return

        if not token:
            print("토큰 없음. 종료.")
            return

        authenticated = await authenticate_with_token(websocket, token)
        if not authenticated:
            return

        # Enter a loop to handle additional requests
        while True:
            print("1. API State Request")
            print("2. Get Current Model")
            print("3. Get the value for all Live2D parameters in the current model")
            print("4. Move mouth to audio file (synchronized)")
            print("5. Heart Eyes On/Off")
            print("6. Eyes Cry On/Off")
            print("7. Angry sign On/Off")
            print("8. Shock sign On/Off")
            print("9. Anim shake On/Off")
            print("0. Exit")

            choice = input("Enter your choice (1/2/3/4/5/6/7/8/9/0): ")

            if choice == "1":
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "APIStateRequest",
                }
                await send_api_request(api_request, websocket)

            elif choice == "2":
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "CurrentModelRequest",
                }
                await send_api_request(api_request, websocket)

            elif choice == "3":
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "Live2DParameterListRequest"
                }
                await send_api_request(api_request, websocket)

            elif choice == "4":
                # Use our new synchronized function
                audio_path = "./audio/output.mp3"
                print(f"Playing audio from {audio_path} with synchronized mouth movements...")
                await play_audio_with_mouth_sync(websocket, audio_path)

            elif choice == "5":
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "HotkeyTriggerRequest",
                    "data": {
                        "hotkeyID": "995d790e63e940e78b43b717ef214756",
                    },
                }
                await send_api_request(api_request, websocket)

            elif choice == "6":
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "HotkeyTriggerRequest",
                    "data": {
                        "hotkeyID": "ac728f4052064ae6b05c58e9290167f9",
                    },
                }
                await send_api_request(api_request, websocket)

            elif choice == "7":
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "HotkeyTriggerRequest",
                    "data": {
                        "hotkeyID": "23b57c8036f240779608c9d246c7716c",
                    },
                }
                await send_api_request(api_request, websocket)

            elif choice == "8":
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "HotkeyTriggerRequest",
                    "data": {
                        "hotkeyID": "8050ec17c3ee41a1b824ee1815407022",
                    },
                }
                await send_api_request(api_request, websocket)

            elif choice == "9":
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "HotkeyTriggerRequest",
                    "data": {
                        "hotkeyID": "0415de2ef49e4943a9bfbe5dfeda3452",
                    },
                }
                await send_api_request(api_request, websocket)

            elif choice == "0":
                print("Exiting the loop.")
                break

            else:
                print("Invalid choice. Please enter 1, 2, 3, 4, 5, or 0.")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())