import librosa
import librosa.display
import pygame


import matplotlib.pyplot as plt

def read_volume():
    # Load the audio file
    audio_file_path = "../gpt-vchat/audio/output.mp3"
    y, sr = librosa.load(audio_file_path)

    # Calculate the root mean square (RMS) energy for each frame
    rms = librosa.feature.rms(y=y)[0]

    # Get the time for each frame
    times = librosa.times_like(rms)

    
    # # Plot the RMS energy over time
    # plt.figure(figsize=(10, 4))
    # librosa.display.waveshow(y, alpha=0.5)
    # plt.plot(times, rms, label='RMS Energy')
    # plt.xlabel('Time (s)')
    # plt.ylabel('RMS Energy')
    # plt.title('RMS Energy over Time')
    # plt.legend()
    # plt.show()
    # read_volume()
    # print(times)
    return times[::10]

def play_audio():
    # Initialize the pygame mixer
    pygame.mixer.init()

    # Load a sound file
    sound_file = "../gpt-vchat/audio/output.mp3"
    sound = pygame.mixer.Sound(sound_file)

    # Play the sound
    sound.play()

    # Wait for the sound to finish playing
    # pygame.time.wait(int(sound.get_length() * 1000))

read_volume()