import os
import asyncio
import websockets
import json
import time
import pygame
import librosa
import numpy as np
import aiohttp
import re
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()
VTUBE_STUDIO_AUTH_TOKEN = os.environ.get("VTUBE_STUDIO_AUTH_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID_OHW")  # OHW voice

# 오디오 파일 저장 경로
AUDIO_DIR = "./audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# OpenAI 스트리밍 응답을 위한 함수
async def stream_openai_response(messages):
    """OpenAI API에서 스트리밍 응답을 받는 함수"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    data = {
        "model": "gpt-4.1",
        "messages": messages,
        "max_tokens": 300,
        "stream": True  # 스트리밍 모드 활성화
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f"Error from OpenAI API: {error_text}")
                yield "죄송합니다, 요청을 처리할 수 없습니다."
                return
            
            # 스트리밍 응답 처리
            buffer = ""
            sentence_end_pattern = re.compile(r'[.!?]\s*')
            
            async for chunk in response.content:
                chunk_text = chunk.decode('utf-8')
                if chunk_text.startswith("data: ") and chunk_text.strip() != "data: [DONE]":
                    try:
                        # "data: " 접두사 제거하고 JSON 파싱
                        json_str = chunk_text[6:]
                        chunk_data = json.loads(json_str)
                        # 델타 콘텐츠 추출
                        if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                            delta = chunk_data["choices"][0].get("delta", {})
                            if "content" in delta:
                                content = delta["content"]
                                buffer += content
                                
                                # 문장이 완성되었는지 확인
                                match = sentence_end_pattern.search(buffer)
                                if match:
                                    sentence_end_idx = match.end()
                                    complete_sentence = buffer[:sentence_end_idx]
                                    buffer = buffer[sentence_end_idx:]
                                    
                                    # 완성된 문장 반환
                                    yield complete_sentence
                    except json.JSONDecodeError:
                        continue
                elif chunk_text.strip() == "data: [DONE]":
                    # 남은 텍스트가 있으면 반환
                    if buffer.strip():
                        yield buffer.strip()
                    break


# TTS 스트리밍 처리를 위한 함수
async def stream_text_to_speech(text, index=0):
    """텍스트를 음성으로 변환하는 함수"""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},  # 스트리밍에 최적화된 설정
    }
    
    tts_start_time = time.time()
    print(f"문장 {index}: TTS 변환 시작...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                # 스트리밍 응답을 파일로 저장
                audio_path = f"{AUDIO_DIR}/output_{index}.mp3"
                with open(audio_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(1024):
                        f.write(chunk)
                
                tts_end_time = time.time()
                print(f"문장 {index}: TTS 처리 완료 ({tts_end_time - tts_start_time:.2f}초)")
                return audio_path
            else:
                error_text = await response.text()
                print(f"Error from ElevenLabs API: {error_text}")
                return None


# 립싱크를 위한 오디오 분석 함수
def analyze_audio(audio_file_path):
    """오디오 파일을 분석하여 타이밍과 입 움직임 값을 반환"""
    # 오디오 로드
    y, sr = librosa.load(audio_file_path)
    
    # RMS 에너지 계산
    hop_length = 512
    frame_length = 2048
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    # 각 프레임의 시간 계산
    times = librosa.times_like(rms, sr=sr, hop_length=hop_length)
    
    # RMS 값을 0-1 범위로 정규화하고 입 움직임 값으로 변환
    normalized_rms = np.interp(rms, (0, rms.max()), (0, 1))
    mouth_values = normalized_rms * 3
    
    return times, mouth_values


# 병렬 처리를 위한 메인 대화 함수
async def parallel_chat_with_character(websocket):
    """스트리밍 방식으로 대화하는 함수"""
    # 대화 기록 초기화
    conversation_history = [
        {"role": "system", "content": "당신은 친절한 어시스턴트입니다."}
    ]
    
    while True:
        print("\n💬 메시지를 입력하세요 ('exit'를 입력하면 메뉴로 돌아갑니다):")
        user_input = input("> ")
        
        if user_input.lower() == "exit":
            return
        
        total_start_time = time.time()
        
        # 사용자 메시지를 대화 기록에 추가
        conversation_history.append({"role": "user", "content": user_input})
        
        # 오디오 큐와 재생 상태를 관리하기 위한 변수들
        audio_queue = asyncio.Queue()
        stop_event = asyncio.Event()
        
        # 생성된 모든 응답 텍스트를 저장할 변수
        full_response = ""
        
        # 1. 오디오 재생 및 립싱크 처리 태스크
        async def process_audio_queue():
            sentence_index = 0
            while not stop_event.is_set() or not audio_queue.empty():
                try:
                    # 큐에서 오디오 파일 경로 가져오기 (1초 타임아웃)
                    audio_path = await asyncio.wait_for(audio_queue.get(), 1.0)
                    
                    # 오디오 분석 및 립싱크 처리
                    print(f"문장 {sentence_index}: 오디오 분석 및 립싱크 시작...")
                    sync_start_time = time.time()
                    
                    await play_audio_with_mouth_sync(websocket, audio_path)
                    
                    sync_end_time = time.time()
                    print(f"문장 {sentence_index}: 립싱크 재생 완료 ({sync_end_time - sync_start_time:.2f}초)")
                    
                    # 처리 완료 표시
                    audio_queue.task_done()
                    sentence_index += 1
                    
                except asyncio.TimeoutError:
                    # 타임아웃 발생시 큐가 비어있고 생성이 중단되었는지 확인
                    if stop_event.is_set() and audio_queue.empty():
                        break
                    continue
        
        # 2. OpenAI에서 응답 스트리밍 및 TTS 변환 태스크
        async def stream_response():
            nonlocal full_response
            sentence_index = 0
            
            async for sentence in stream_openai_response(conversation_history):
                if sentence:
                    print(f"문장 {sentence_index} 수신: {sentence}")
                    full_response += sentence
                    
                    # TTS 변환 및 오디오 큐에 추가
                    audio_path = await stream_text_to_speech(sentence, sentence_index)
                    if audio_path:
                        await audio_queue.put(audio_path)
                    
                    sentence_index += 1
            
            # 모든 응답 처리 완료 표시
            stop_event.set()
            
            # 대화 기록에 어시스턴트 응답 추가
            conversation_history.append({"role": "assistant", "content": full_response})
            print(f"\n전체 응답: {full_response}")
        
        # 두 태스크를 동시에 실행
        await asyncio.gather(
            stream_response(),
            process_audio_queue()
        )
        
        # 임시 오디오 파일 정리
        for filename in os.listdir(AUDIO_DIR):
            if filename.startswith("output_"):
                os.remove(os.path.join(AUDIO_DIR, filename))
        
        # 전체 처리 시간 계산 및 표시
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        print(f"\n⏱️ 전체 처리 시간: {total_duration:.2f}초")


# 오디오 재생 및 립싱크 함수 (기존 함수 최적화)
async def play_audio_with_mouth_sync(websocket, audio_path):
    """오디오를 재생하고 립싱크를 처리하는 함수"""
    # 오디오 분석
    times, mouth_values = analyze_audio(audio_path)
    
    # MouthOpenAmount 파라미터가 존재하는지 확인하고 필요하면 생성
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
    await send_api_request(creation_request, websocket, silent=True)
    
    # 오디오 재생 준비
    pygame.mixer.init()
    sound = pygame.mixer.Sound(audio_path)
    
    # 타이밍 변수 설정
    frame_count = len(times)
    current_frame = 0
    
    # 오디오 재생 시작
    sound.play()
    start_time = time.time()
    
    # 메인 동기화 루프
    while current_frame < frame_count:
        # 경과 시간 기반 프레임 계산
        elapsed_time = time.time() - start_time
        target_frame = 0
        
        # 현재 시간에 맞는 프레임 찾기
        while target_frame < frame_count and times[target_frame] < elapsed_time:
            target_frame += 1
        
        if target_frame >= frame_count:
            break
        
        # 새 프레임으로 이동할 때만 업데이트
        if target_frame > current_frame:
            current_frame = target_frame
            mouth_value = mouth_values[current_frame]
            
            # 더 뚜렷한 움직임을 위한 스케일링
            scaled_value = min(mouth_value * 20, 100)
            
            # VTube Studio에 파라미터 전송
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
        
        # 요청 폭주 방지를 위한 짧은 대기
        await asyncio.sleep(0.01)
    
    # 오디오 재생 완료 대기
    remaining_time = sound.get_length() - elapsed_time
    if remaining_time > 0:
        await asyncio.sleep(remaining_time)
    
    # 입 닫기 위치로 재설정
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
    await send_api_request(reset_request, websocket, silent=True)


# VTube Studio API 요청 전송 함수
async def send_api_request(request, websocket, silent=False):
    """VTube Studio API 요청을 전송하는 함수"""
    api_request_json = json.dumps(request)
    await websocket.send(api_request_json)
    response = await websocket.recv()
    if not silent:
        response_json = json.loads(response)
        print(json.dumps(response_json, indent=4))
        return response_json
    return json.loads(response)


# 인증 토큰 요청 함수
async def request_auth_token(websocket):
    """인증 토큰을 요청하는 함수"""
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
    print("\n🔑 인증 토큰 요청 중...")
    response = await send_api_request(token_request, websocket)
    
    if response["messageType"] == "AuthenticationTokenResponse":
        token = response["data"]["authenticationToken"]
        print(f"\n✅ 토큰 수신: {token}")
        return token
    elif response["messageType"] == "APIError":
        print(f"\n❌ 오류: {response['data']['message']}")
        return None
    else:
        print("\n❌ 예상치 못한 응답.")
        return None


# 토큰으로 인증 함수
async def authenticate_with_token(websocket, token):
    """토큰으로 인증하는 함수"""
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
    print("\n🔐 토큰으로 인증 중...")
    response = await send_api_request(auth_request, websocket)
    
    if (
        response["messageType"] == "AuthenticationResponse"
        and response["data"]["authenticated"]
    ):
        print("\n✅ 플러그인 인증 성공!")
        return True
    else:
        print("\n❌ 인증 실패.")
        return False


# 메인 함수
async def main():
    """메인 함수"""
    uri = "ws://localhost:8001"
    
    async with websockets.connect(uri) as websocket:
        print("1. 입력된 토큰 사용")
        print("2. 새로 토큰 요청 (팝업 뜸)")
        token_option = input("선택 (1/2): ")
        
        token = None
        if token_option == "1":
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
        
        # 메뉴 루프
        while True:
            print("\n=== VTube Studio 컨트롤 메뉴 ===")
            print("1. API 상태 요청")
            print("2. 현재 모델 가져오기")
            print("3. 현재 모델의 모든 Live2D 파라미터 값 가져오기")
            print("4. 병렬 처리로 캐릭터와 대화하기")  # 새로운 스트리밍 대화 옵션
            print("5. 하트 눈 켜기/끄기")
            print("6. 눈물 켜기/끄기")
            print("7. 화난 표시 켜기/끄기")
            print("8. 놀란 표시 켜기/끄기")
            print("9. 흔들림 애니메이션 켜기/끄기")
            print("0. 종료")
            
            choice = input("선택하세요 (0-9): ")
            
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
                    "messageType": "Live2DParameterListRequest",
                }
                await send_api_request(api_request, websocket)
            
            elif choice == "4":
                # 새로운 병렬 처리 대화 함수 호출
                await parallel_chat_with_character(websocket)
            
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
                print("프로그램을 종료합니다.")
                break
            
            else:
                print("잘못된 선택입니다. 0부터 9 사이의 숫자를 입력하세요.")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())