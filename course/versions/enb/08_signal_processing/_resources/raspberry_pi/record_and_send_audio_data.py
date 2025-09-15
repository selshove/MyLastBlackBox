import pyaudio
import socket
import numpy as np


# Host PC IP address and port number
SERVER_IP = '10.63.8.27'
SERVER_PORT = 5005


CHUNK_SIZE = 4096           # Buffer size
FORMAT = pyaudio.paInt16    # Data type
CHANNELS = 2                # Number of channels
RATE = 44100                # Sample rate (Hz)

def send_audio():
    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    INPUT_DEVICE_INDEX = 1

    # Open the audio stream
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index = INPUT_DEVICE_INDEX,
                        frames_per_buffer=CHUNK_SIZE)

    # Create a socket and connect to the server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_IP, SERVER_PORT))

    try:
        while True:
            # Read audio data from the stream
            data = stream.read(CHUNK_SIZE,exception_on_overflow=False)

            # Send the audio data over the network
            client_socket.sendall(data)
    except KeyboardInterrupt:
        # Close the stream and socket when interrupted
        stream.stop_stream()
        stream.close()
        client_socket.close()

if __name__ == '__main__':
    send_audio()