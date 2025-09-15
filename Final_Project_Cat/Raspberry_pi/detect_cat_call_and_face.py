import pyaudio
import numpy as np
from scipy.fft import rfft, rfftfreq
import serial
import threading
import time
import io

CHUNK_SIZE = 4096           # Buffer size
FORMAT = pyaudio.paInt16    # Data type
CHANNELS = 2                # Number of channels
RATE = 44100                # Sample rate (Hz)


# Global flag accessible from other scripts
whistle_detected = 1

def detect_whistling_thread():
    global whistle_detected
    
    audio = pyaudio.PyAudio()
    INPUT_DEVICE_INDEX = 1


    try:
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index = INPUT_DEVICE_INDEX,
            frames_per_buffer=CHUNK_SIZE
        )
    except Exception as e:
        print("Failed to open audio stream:", e)
        return

    print("Sound detection thread started...")

    while True:
        try:
            raw_data = stream.read(CHUNK_SIZE, exception_on_overflow=False)

        except Exception as e:
            print("Audio processing error:", e)
            time.sleep(0.1)
            whistle_detected = False

        interleaved_data = np.frombuffer(raw_data, dtype=np.int16)
        left = interleaved_data[::2]  # Left channel only
        right = interleaved_data[1::2]  

        fourier = np.abs(rfft(left))
        freqs = rfftfreq(len(left), 1 / RATE)

        max_amplitude_index = np.argmax(fourier)
        frequency = freqs[max_amplitude_index]
        amplitude = fourier[max_amplitude_index]

     
        # Whistle frequency range
        if 3000 < frequency < 8000:
            whistle_detected = 1
            print("HEARING")
        else:
            whistle_detected = 2
            print("no sound")

        time.sleep(0.05)