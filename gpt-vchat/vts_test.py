import websockets
import json
import time
from readvolume import read_volume
from readvolume import play_audio

async def send_api_request(request, websocket):
    # Convert the API request to a JSON string
    api_request_json = json.dumps(request)

    # Send the JSON string as a text message
    await websocket.send(api_request_json)

    # Wait for the response
    response = await websocket.recv()
    # print("Received response:", response)
    response_json = json.loads(response)
    # print(type(response))
    # print(json.dumps(response_json, indent=4))
    
# Hot Key Trigger (ex. blush, cool, worried, browslink, ...)
async def hotkeyTrigger(websocket, type):
    type_dict = {
            "blush":"657ce364943c45f6843795602f8f471e", 
            "cool":"d0f87fb668f44e738c5e4ec162b09ac7",
            "worried":"294bae3450e6428caba43e0bcf6d3038",
            "browlink":"49a3e4afab744c32b3ed561fd7e2738b",
            "akari_animshake":"0415de2ef49e4943a9bfbe5dfeda3452",
            "akari_hearteyes":"995d790e63e940e78b43b717ef214756"
            }
    api_request = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": "SomeID",
        "messageType": "HotkeyTriggerRequest",
        "data": {    
            "hotkeyID": type_dict[type],              
            # "itemInstanceID": "Optional_ItemInstanceIdOfLive2DItemToTriggerThisHotkeyFor"
        }
    }
    await send_api_request(api_request, websocket)	


async def move_mouth():
    uri = "ws://localhost:8001"
    async with websockets.connect(uri) as websocket:

        print("(Sending Auth Request)")
        # Authentication request : 나중엔 얘는 따로 떼서 최초 한 번만 실행되게 하기)
        authentication_request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "SomeID",
            "messageType": "AuthenticationRequest",
            "data": {
                "pluginName": "VtsTestPlugin",
                "pluginDeveloper": "Patcasso",
                "authenticationToken": "2a301c169293fae6635dc62ff5104c4385f4039d767bb9ba304be888cd8a1a27"
            }
        }
        await send_api_request(authentication_request, websocket)

        # Hot Key Trigger On
        emotion = "akari_hearteyes"
        await hotkeyTrigger(websocket, emotion)

        print("(Playing audio file and moving mouth)")
        values = read_volume()
        audio_length = play_audio()

        print(f"audio_length: {audio_length}, len(values): {len(values)}")

        # 오디오 길이에 비례해 입모양 움직이는 코드
        for i in range(len(values)):
            value = (values[i] // 3) if i % 3 == 0 else values[i]
            # value = values[i]
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
                        {
                            "id": "MouthOpenAmount",
                            "value": value * 20
                        },
                    ]
                }
            }
            await send_api_request(api_request, websocket)
            
            # 대답 오디오 길이를 총 루프 수로 나눈 만큼 기다리기
            time.sleep(audio_length / len(values))

        # Hot Key Trigger Off
        await hotkeyTrigger(websocket, emotion)
        await hotkeyTrigger(websocket, "blush")

# if __name__ == "__main__":
# def vts_loop():
#     asyncio.get_event_loop().run_until_complete(main())
