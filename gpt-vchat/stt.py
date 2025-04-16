import queue
import re

# import sys
from gpt import run_gpt
# from tts import create_tts
from tts import play_tts

from tts_eleven import *

from google.cloud import speech # https://velog.io/@minbrok/Google-STT-API-%EC%82%AC%EC%9A%A9%ED%95%B4%EB%B3%B4%EA%B8%B0
# 필요한 다른 라이브러리들 설치
import pyaudio # https://ungodly-hour.tistory.com/35
# 홈브루로 portaudio 부터 설치, 

import asyncio
from vts_test import *

# Audio recording parameters
RATE = 44100
CHUNK = int(RATE / 10)  # 100ms
# SILENCE_THRESHOLD = 0.01  # Adjust this value according to your needs


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate=RATE, chunk=CHUNK):
        """The audio -- and generator -- is guaranteed to be on the main thread."""
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        """Closes the stream, regardless of whether the connection was lost or not."""
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer.

        Args:
            in_data: The audio data as a bytes object
            frame_count: The number of frames captured
            time_info: The time information
            status_flags: The status flags

        Returns:
            The audio data as a bytes object
        """
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        """Generates audio chunks from the stream of audio data in chunks.

        Args:
            self: The MicrophoneStream object

        Returns:
            A generator that outputs audio chunks.
        """
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)


def listen_print_loop(responses, persona, gpt_messages):
    """Iterates through server responses and prints them.
    The responses passed is a generator that will block until a response
    is provided by the server.
    Each response may contain multiple results, and each result may contain
    multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
    print all available alternatives for each result.
    Args:
        responses: List of server responses
    Returns:
        The transcribed text.
    """
    transcript = ""

    for response in responses:
        if not response.results:
            continue

        for result in response.results:
            stability = result.stability
            # print(result)
            # print("Stability: " + str(stability))

            if not result.alternatives:
                continue

            for alternative in result.alternatives: # 지 목소리 인식 안시키려고 하는 기능도 있음
                transcript = alternative.transcript
                confidence = alternative.confidence

                # 사용자 목소리 인식해 프롬프트로 전달
                
                print("User: " + transcript)
                gpt_messages.append({"role": "user", "content": transcript})
                break

            # GPT 응답 받아서 출력 후, 목소리로 만들어 재생
            answer = run_gpt(gpt_messages)
            print(f"{persona['name']}: " + answer)

            # GPT 대답 대화 기록에 추가
            gpt_messages.append({"role": "system", "content": answer})

            # 음성 파일 생성
            # create_tts(answer)
            send_request(answer)

            break
        # VTS Studio에서 입모양 움직이기
        asyncio.run(move_mouth())
        
        # 단순 음성 재생
        # play_tts("./audio/output.mp3")

       
        break

        # if response.results[0].is_final:
        #     if re.search(r"\b(exit|quit)\b", transcript, re.I):
        #         print("Exiting...")
        #         break

    return gpt_messages


def sound_to_text(gpt_messages, persona):
    """Transcribe speech from audio file."""
    # language_code = "en-US"  # a BCP-47 language tag
    language_code = "ko-KR"  # a BCP-47 language tag

    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code,
        enable_word_time_offsets=True,
        enable_automatic_punctuation=True,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        # single_utterence - (optional, defaults to false) indicates whether this request should automatically end after speech is no longer detected
        # single_utterance=True,
        interim_results=False,
        # interim_results=True,
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )

        responses = client.streaming_recognize(streaming_config, requests)

        return listen_print_loop(responses, persona, gpt_messages)


if __name__ == "__main__":
    sound_to_text()
