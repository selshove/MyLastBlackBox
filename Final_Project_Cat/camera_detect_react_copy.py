#!/usr/bin/env python3
import os
import time
import threading
from picamera2 import Picamera2
from flask import Flask, Response, render_template_string
from PIL import Image
import numpy as np
import cv2
import serial
import io

# Suppress warnings
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["ALSA_CARD"] = "default"

from Raspberry_pi.detect_cat_call_and_face import detect_whistling_thread, whistle_event


# Serial setup
ser = serial.Serial()
ser.baudrate = 115200
ser.port = '/dev/ttyUSB0'
try:
    ser.open()
except Exception as e:
    print("[Serial] Could not open serial port:", e)
time.sleep(2)

# Camera setup
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 360), "format": "RGB888"})
picam2.configure(config)
picam2.start()

latest_jpeg = None
cv_cond = threading.Condition()
running = True

def capture_loop():
    global latest_jpeg, running
    print("[Camera] Capture thread started")
    last_sent_command = None
    last_command_time = 0
    face_timeout = 1.0
    last_seen_face_time = time.time()
    command_interval = 0.1  # seconds (100ms)

    det = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    if det.empty():
        print("[Camera] ERROR: Failed to load cascade classifier.")
        return

    while running:
        try:
            frame_rgb = picam2.capture_array()
            print("[Camera] Captured frame")

            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Run face detection
            rects = det.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
            print(f"[Camera] Detected {len(rects)} face(s)")

            # ... rest of your logic ...
            current_time = time.time()

            print("whistle_detected =")
            print(whistle_detected)

            if whistle_detected == 1:
                print("DHIUDFIUGHUIDFGIHUODFGHIDFUHGIDF")

                if len(rects) > 0:
                    # Face detected
                    last_seen_face_time = current_time  # update timestamp

                    for (x, y, w, h) in rects:

                        frame_h, frame_w = frame.shape[:2]
                        f_center = (frame_w // 2, frame_h // 2)
                        cv2.circle(frame, f_center, 8, (255, 0, 0), -1)  # blue dot
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 5)

                        rx = x + (w//2)
                        ry = y + (h//2)
                        r_center = (rx, ry)
                        cv2.circle(frame, r_center, 8, (0, 0, 255), -1)  # red dot

                        cv2.line(frame, f_center, r_center, (0, 165, 255), 3)  # orange line

                        current_time = time.time()
                        if current_time - last_command_time > command_interval:
                            print(".............................")
                            if ry < frame_h // 2 - 50:
                                if last_sent_command != 'f':
                                    ser.write(b'f')
                                    last_sent_command = 'f'
                            elif rx > frame_w // 2 + 50:
                                if last_sent_command != 'r':
                                    ser.write(b'r')
                                    last_sent_command = 'r'
                            elif rx < frame_w // 2 - 50:
                                if last_sent_command != 'l':
                                    ser.write(b'l')
                                    last_sent_command = 'l'
                            else:
                                if last_sent_command != 'x':
                                    ser.write(b'x')  # center aligned
                                    last_sent_command = 'x'

                            last_command_time = current_time

                else:
                    # No face detected
                    if current_time - last_seen_face_time > face_timeout:
                        if last_sent_command != 'x':
                            ser.write(b'x')  # stop
                            last_sent_command = 'x'
                    # JPEG encode
                    buf = io.BytesIO()
                    Image.fromarray(frame).save(buf, format="JPEG", quality=85)
                    jpeg = buf.getvalue()

                    with cv_cond:
                        latest_jpeg = jpeg
                        cv_cond.notify_all()
            #else:

        except Exception as e:
            print(f"[Camera] ERROR: {e}")
            time.sleep(1)  # avoid tight retry loop

        time.sleep(0.01)

        # Prepare JPEG
        if len(frame.shape) == 2:
            frame = np.repeat(frame[..., None], 3, axis=2).astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(frame).save(buf, format="JPEG", quality=85, optimize=True)
        jpeg = buf.getvalue()
        with cv_cond:
            latest_jpeg = jpeg
            cv_cond.notify_all()

        time.sleep(0.01)

# Start threads
audio_thread = threading.Thread(target=detect_whistling_thread, daemon=True)
audio_thread.start()

capture_thread = threading.Thread(target=capture_loop, daemon=True)
capture_thread.start()

app = Flask(__name__)
INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Raspberry Pi Camera</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:#111; color:#eee; }
    header { padding: 12px 16px; background:#000; position: sticky; top:0; }
    main { display:flex; justify-content:center; align-items:center; min-height: calc(100vh - 52px); }
    img { max-width: 100%; height: auto; background:#000; }
    .bar { display:flex; gap:12px; align-items:center; }
    a,button { color:#eee; text-decoration:none; background:#222; border:1px solid #333; padding:8px 12px; border-radius:8px; }
    a:hover,button:hover { background:#333; }
  </style>
</head>
<body>
  <header>
    <div class="bar">
      <strong>Raspberry Pi Live Stream</strong>
      <a href="/snapshot.jpg" target="_blank">Snapshot</a>
    </div>
  </header>
  <main>
    <img src="/stream.mjpg" alt="Live Stream (MJPEG)" />
  </main>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/snapshot.jpg")
def snapshot():
    # return the latest JPEG once
    with cv_cond:
        if latest_jpeg is None:
            # block briefly for first frame
            cv_cond.wait(timeout=1.0)
        data = latest_jpeg or b""
    return Response(data, mimetype="image/jpeg")

@app.route("/stream.mjpg")
def mjpeg():
    def gen():
        boundary = "--frame"
        # Send an initial frame quickly if we have one
        last = None
        while True:
            with cv_cond:
                if latest_jpeg is None:
                    cv_cond.wait(timeout=1.0)
                # Only push when we have a new frame
                if latest_jpeg is last:
                    cv_cond.wait(timeout=0.05)
                data = latest_jpeg
                last = data
            if data is None:
                continue
            yield (
              b"--frame\r\n"
              b"Content-Type: image/jpeg\r\n"
              b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n"
            )
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

def cleanup():
    global running
    running = False
    try:
        picam2.stop()
    except Exception as e:
        print("[Camera] Stop error:", e)
    try:
        ser.close()
    except:
        pass

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=8000, threaded=True)
    finally:
        cleanup()
