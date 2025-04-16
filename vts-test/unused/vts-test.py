import asyncio
import websockets
import json
import time
import threading
import pygame
from readvolume import read_volume, play_audio


async def send_api_request(request, websocket):
    api_request_json = json.dumps(request)
    await websocket.send(api_request_json)
    response = await websocket.recv()
    response_json = json.loads(response)
    print(json.dumps(response_json, indent=4))
    return response_json


async def request_auth_token(websocket):
    token_request = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": "TokenRequestID",
        "messageType": "AuthenticationTokenRequest",
        "data": {
            "pluginName": "VtsTestPlugin",
            "pluginDeveloper": "Patcasso",
            # base64 icon 128x128 optional
            # "pluginIcon": "iVBORw0KGgoAAAANSUhEUgAAAIwAAACMCAIAAAD6n...",
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


async def main():
    uri = "ws://localhost:8001"

    # async with websockets.connect(uri) as websocket:
    #     # Authentication request
    #     authentication_request = {
    #         "apiName": "VTubeStudioPublicAPI",
    #         "apiVersion": "1.0",
    #         "requestID": "SomeID",
    #         "messageType": "AuthenticationRequest",
    #         "data": {
    #             "pluginName": "VtsTestPlugin",
    #             "pluginDeveloper": "Patcasso",
    #             "authenticationToken": "2a301c169293fae6635dc62ff5104c4385f4039d767bb9ba304be888cd8a1a27"
    #         }
    #     }

    #     await send_api_request(authentication_request, websocket)

    async with websockets.connect(uri) as websocket:
        print("1. 입력된 토큰 사용")
        print("2. 새로 토큰 요청 (팝업 뜸)")
        token_option = input("선택 (1/2): ")

        token = None
        if token_option == "1":
            token = input("저장된 토큰 입력: ")
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
            # print("3. Move Model")
            print("3. Get the value for all Live2D parameters in the current model")
            # print("3. Custom request")
            # print("4. Request available hotkeys")
            # print("4. Control Mouth Open Amount(0-100)")
            print("4. Move mouth to audio file")
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
                print(type(api_request))
                await send_api_request(api_request, websocket)

            elif choice == "3":
                print("Enter custom API request")
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "ParameterCreationRequest",
                    "data": {
                        "parameterName": "MouthOpenAmount",
                        "explanation": "Controls the amount of mouth open.",
                        "min": 0,
                        "max": 100,
                        "defaultValue": 0,
                    },
                }
                # api_request = {
                # 	"apiName": "VTubeStudioPublicAPI",
                # 	"apiVersion": "1.0",
                # 	"requestID": "SomeID",
                # 	"messageType": "MoveModelRequest",
                # 	"data": {
                # 		"timeInSeconds": 0.2,
                # 		"valuesAreRelativeToModel": False,
                # 		"positionX": 0.1,
                # 		"positionY": -0.7,
                # 		"rotation": 0,
                # 		"size": -50.5
                # 	}
                # }

                # api_request = {
                #     "apiName": "VTubeStudioPublicAPI",
                #     "apiVersion": "1.0",
                #     "requestID": "SomeID",
                #     "messageType": "Live2DParameterListRequest"
                # }

                # api_request = {
                #     "apiName": "VTubeStudioPublicAPI",
                #     "apiVersion": "1.0",
                #     "requestID": "SomeID",
                #     "messageType": "InputParameterListRequest"
                # }

                await send_api_request(api_request, websocket)

            elif choice == "4":
                # api_request = {
                # 	"apiName": "VTubeStudioPublicAPI",
                # 	"apiVersion": "1.0",
                # 	"requestID": "SomeID",
                # 	"messageType": "HotkeysInCurrentModelRequest",
                # 	"data": {
                #         # Akari
                # 		# "modelID": "853f95fd8dc34944a94bd526f19530a8",
                #         # LiveroioD_A-Y01
                # 		"modelID": "d54ca70deb8b45798e2969e997edb087",
                # 		"live2DItemFileName": "Optional_Live2DItemFileName"
                # 	}
                # }
                # 1. 커스텀 파라미터 등록 (이미 등록된 경우에도 재전송 OK)
                creation_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "ParamCreate_MouthOpenAmount",
                    "messageType": "ParameterCreationRequest",
                    "data": {
                        "parameterName": "MouthOpenAmount",  # 커스텀 트래킹 파라미터
                        "explanation": "Controls the amount of mouth open from audio volume.",
                        "min": 0,
                        "max": 100,
                        "defaultValue": 0,
                    },
                }
                print("\n📌 Creating custom tracking parameter 'MouthOpenAmount'...")
                await send_api_request(creation_request, websocket)

                # 2. 오디오 기반으로 mouth open 값 계산

                def start_audio():
                    pygame.mixer.init()
                    sound = pygame.mixer.Sound("../gpt-vchat/audio/output.mp3")
                    sound.play()
                    
                # 1. 오디오 볼륨 값 미리 분석
                values = read_volume()

                # 2. 오디오 재생을 백그라운드로 실행
                threading.Thread(target=start_audio).start()
               
                # play_audio()
                for i in range(len(values)):
                    time.sleep(0.1)
                    value = values[i] if i % 2 == 0 else 0
                    # mouth_open_amount = input()
                    # if mouth_open_amount == "x":
                    #     break
                    api_request = {
                        "apiName": "VTubeStudioPublicAPI",
                        "apiVersion": "1.0",
                        "requestID": "SomeID",
                        "messageType": "InjectParameterDataRequest",
                        "data": {
                            "faceFound": False,
                            "mode": "set",
                            "parameterValues": [
                                {"id": "MouthOpenAmount", "value": value * 20},
                                # {"id": "MouthOpenAmount", "value": value},
                            ],
                        },
                    }
                    await send_api_request(api_request, websocket)

            elif choice == "5":
                api_request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "SomeID",
                    "messageType": "HotkeyTriggerRequest",
                    "data": {
                        "hotkeyID": "995d790e63e940e78b43b717ef214756",
                        # "itemInstanceID": "Optional_ItemInstanceIdOfLive2DItemToTriggerThisHotkeyFor"
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
                        # "itemInstanceID": "Optional_ItemInstanceIdOfLive2DItemToTriggerThisHotkeyFor"
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
                        # "itemInstanceID": "Optional_ItemInstanceIdOfLive2DItemToTriggerThisHotkeyFor"
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
                        # "itemInstanceID": "Optional_ItemInstanceIdOfLive2DItemToTriggerThisHotkeyFor"
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
                        # "itemInstanceID": "Optional_ItemInstanceIdOfLive2DItemToTriggerThisHotkeyFor"
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
