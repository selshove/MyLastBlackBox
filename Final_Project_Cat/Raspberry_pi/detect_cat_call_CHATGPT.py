import pyaudio
import numpy as np
from scipy.fft import rfft, rfftfreq
import serial
import time
import subprocess
import threading

CHUNK_SIZE = 4096           # Buffer size
FORMAT = pyaudio.paInt16    # Data type
CHANNELS = 2                # Number of channels
RATE = 44100               # Sample rate (Hz)


def play_sound():
    # Run aplay in a separate thread to avoid blocking the main loop
    def _play():
        subprocess.run([
        "sox", "cat.wav", "-d", "vol", "3.0"])

        subprocess.run([
            "aplay", "-D", "plughw:3", "-c2",
            "-r", "48000", "-f", "S16_le",
            "-t", "wav", "-V", "stereo", "-v", "cat.wav"
        ])
    threading.Thread(target=_play, daemon=True).start()


def detect_whistling():
    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    INPUT_DEVICE_INDEX = 1

    # Open the audio stream
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=INPUT_DEVICE_INDEX,
                        frames_per_buffer=CHUNK_SIZE)

    # Open serial connection to send instructions to the Arduino
    ser = serial.Serial('/dev/ttyUSB0', 115200)
    try:
        ser.open()
    except:
        ser.close()
        ser.open()

    target_frequency_min = 2000
    target_frequency_max = 8000

    sound_played = False  # Move outside loop to persist state
    cooldown = 2.0        # seconds between allowed triggers
    last_trigger_time = 0

    try:
        while True:
            # Read audio data from the stream
            raw_data = stream.read(CHUNK_SIZE, exception_on_overflow=False)

            # Convert raw_data to left and right channel
            interleaved_data = np.frombuffer(raw_data, dtype=np.int16)
            left = interleaved_data[::2]
            # right = interleaved_data[1::2]  # Unused here

            # Compute Fourier transform on left channel
            fourier = np.abs(rfft(left))
            freqs = rfftfreq(len(left), 1 / RATE)

            max_amplitude_index = np.argmax(fourier)
            frequency = freqs[max_amplitude_index]

            cur_frequency = frequency

            current_time = time.time()

            if target_frequency_min < cur_frequency < target_frequency_max:
                ser.write(b'f')
                print(f"HEARING - {cur_frequency:.2f} Hz")

                # Trigger sound and command only if cooldown passed and not already triggered
                if not sound_played and (current_time - last_trigger_time) > cooldown:
                    print("PLAYING")
                    play_sound()
                    sound_played = True
                    last_trigger_time = current_time

            else:
                ser.write(b'x')
                print("no sound")
                sound_played = False

    except KeyboardInterrupt:
        # Close the stream and serial port cleanly on exit
        stream.stop_stream()
        stream.close()
        ser.close()
        audio.terminate()


if __name__ == '__main__':
    detect_whistling()
