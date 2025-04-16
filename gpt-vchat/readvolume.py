import librosa
import librosa.display
import pygame


import matplotlib.pyplot as plt


def read_volume():
    # Load the audio file
    audio_file_path = "./audio/output.mp3"
    y, sr = librosa.load(audio_file_path)

    # Calculate the root mean square (RMS) energy for each frame
    rms = librosa.feature.rms(y=y)[0]

    # Get the time for each frame
    times = librosa.times_like(rms)

    # # Plot the RMS energy over time (시각화에만 필요한 코드 부분)
    # plt.figure(figsize=(10, 4))
    # librosa.display.waveshow(y, alpha=0.5)
    # plt.plot(times, rms, label="RMS Energy")
    # plt.xlabel("Time (s)")
    # plt.ylabel("RMS Energy")
    # plt.title("RMS Energy over Time")
    # plt.legend()
    # plt.show()

    # read_volume()
    # print(times)
    return times[::6]  # RMS 정보가 너무 촘촘해 6개 간격으로 보내는 것


def play_audio():
    # Initialize the pygame mixer
    pygame.mixer.init()

    # Load a sound file
    sound_file = "./audio/output.mp3"
    sound = pygame.mixer.Sound(sound_file)

    # Play the sound
    sound.play()

    # Wait for the sound to finish playing
    # pygame.time.wait(int(sound.get_length() * 1000))

    # 오디오 길이를 return
    return pygame.time.wait(int(sound.get_length()))


# read_volume()
