import pyaudio
import numpy as np
from scipy.fft import rfft, rfftfreq
import serial


CHUNK_SIZE = 4096           # Buffer size
FORMAT = pyaudio.paInt16    # Data type
CHANNELS = 1                # Number of channels
RATE = 44100 #22050                # Sample rate (Hz)


def detect_whistling():
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

    # Open serial connection to send instructions to the arduino
    ser = serial.Serial('/dev/ttyUSB0', 115200)
    try:
        ser.open()
    except:
        ser.close()
        ser.open()

    try:
        while True:
            # Read audio data from the stream
            raw_data = stream.read(CHUNK_SIZE,exception_on_overflow=False)

            # Convert raw_data to left and right channel
            interleaved_data = np.frombuffer(raw_data, dtype=np.int16)
            left = interleaved_data[::2] 
            right = interleaved_data[1::2]  

            # calculate Fourier transform
            #############################
            ### COMPUTE THE FOURIER TRANSFORM using RFFT and RFFTFREQ
            #############################
            # Write your code, you need either the "left" and/or the "right" variable
            
            fourier = np.abs(rfft(left))
            freqs = rfftfreq(len(left), 1 / RATE)

            max_amplitude_index = np.argmax(fourier)
            frequency = freqs[max_amplitude_index]

            # find the frequency with the highest amplitude
            ##########################
            ##### IDENTIFY THE CURRENT DOMINANT FREQUENCY
            ##### and THE AMPLITUDE
            ##### replace the cur_frequency = 0 with your code
            ##########################
            cur_frequency = frequency


            target_frequency_max = 8000 # this is the frequency you determined with the recorded audio file
            target_frequency_min = 2000
            if cur_frequency > target_frequency_min and cur_frequency < target_frequency_max:
                # Send intructions to the robot
                ser.write(b'f')
                print("HEARING")
            
                

            else:
                # Send intructions to the robot
                ser.write(b'x')
                print("no sound")
                
    except KeyboardInterrupt:
        # Close the stream and socket when interrupted
        stream.stop_stream()
        stream.close()
        ser.close()

if __name__ == '__main__':
    detect_whistling()