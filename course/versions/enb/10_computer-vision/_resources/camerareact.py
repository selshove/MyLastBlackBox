#!/usr/bin/env python3
from picamera2 import Picamera2
from flask import Flask, Response, render_template_string, send_file
import threading, io, time
from PIL import Image
import numpy as np
import cv2
import serial
import time
import curses


# get the curses screen window
screen = curses.initscr()

# turn off input echoing
curses.noecho()

# respond to keys immediately (don't wait for enter)
curses.cbreak()

# map arrow keys to special values
screen.keypad(True)

# Configure serial port
ser = serial.Serial()
ser.baudrate = 115200
ser.port = '/dev/ttyUSB0'

# Open serial port
ser.open()
time.sleep(2.00) # Wait for connection before sending any data


# --- Camera setup ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (1280//2, 720//2), "format": "RGB888"}  # tweak resolution/format as needed
)
picam2.configure(config)
picam2.start()

# --- Frame grab thread ---
latest_jpeg = None
cv = threading.Condition()
running = True

def capture_loop():
    global latest_jpeg, running, last_command, last_command_time
    last_command = None
    last_command_time = 0
    command_delay = 0.1  # 100 ms between commands
    
    while running:
        # Grab frame as numpy array (RGB888)
        #frame = picam2.capture_array()[:,:,::-1]
        rgb_frame = picam2.capture_array()
        frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)


        #################################################
        ### HERE WE CAN DO RANDOM STUFF TO THE FRAME  ###
        #################################################
        det = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
        rects = det.detectMultiScale(gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(50, 50), # adjust to your image size, maybe smaller, maybe larger?
            flags=cv2.CASCADE_SCALE_IMAGE)

        
        frame_h, frame_w = frame.shape[:2]
        f_center = (frame_w // 2, frame_h // 2)
        cv2.circle(frame, f_center, 8, (255, 0, 0), -1)  # blue dot

        for (x, y, w, h) in rects:
            # x: x location
            # y: y location
            # w: width of the rectangle 
            # h: height of the rectangle
            # Remember, order in images: [y, x, channel]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 10)

            rx = x + (w//2)
            ry = y + (h//2)
            r_center = (rx, ry)
            cv2.circle(frame, r_center, 8, (0, 0, 255), -1)  # red dot

            cv2.line(frame, f_center, r_center, (0, 165, 255), 3)  # orange line


            # Decide direction
            dy = ry - f_center[1]
            dx = rx - f_center[0]

            direction = None
            threshold = 30  # deadzone to avoid micro-movements

            if abs(dx) > abs(dy):
                if dx > threshold:
                    direction = 'r'  # face is right of center
                elif dx < -threshold:
                    direction = 'l'  # face is left of center
            else:
                if dy < -threshold:
                    direction = 'f'  # face is above center
                elif dy > threshold:
                    direction = 'x'  # face is below center, stop

            # Send command only if changed and delay passed
            now = time.time()
            if direction and direction != last_command and now - last_command_time > command_delay:
                ser.write(direction.encode())
                last_command = direction
                last_command_time = now


            # try:
            #     while True:
            #         char = screen.getch()   
            #         if char == ord('q'):
            #             break
            #         elif char == ord('x'):
            #             screen.addstr(0, 0, 'STOP ')
            #             ser.write(b'x')
            #             time.sleep(0.05)
            #         elif frame_h > ry:
            #             screen.addstr(0, 0, 'right')
            #             ser.write(b'r')
            #             time.sleep(0.05)
            #         elif ry > frame_h:
            #             screen.addstr(0, 0, 'left ')       
            #             ser.write(b'l')
            #             time.sleep(0.05)
            #         elif ry == frame_h:
            #             screen.addstr(0, 0, 'up   ')       
            #             ser.write(b'f')
            #             time.sleep(0.05)
            #         # elif char == curses.KEY_DOWN:
            #         #     screen.addstr(0, 0, 'down ')
            #         #     ser.write(b'b')
            #         #     time.sleep(0.05)
            # finally:
            #     # shut down
            #     curses.nocbreak(); screen.keypad(0); curses.echo()
            #     curses.endwin()
            #     ser.close()



        # And here it gets converted and so on...
        #frame = frame.astype(np.float32)
        #frame = (frame - frame.min()) / (frame.max() - frame.min()) * 255

        if len(frame.shape) == 2:
            frame = np.repeat(frame[..., None], 3, 2).astype(np.uint8)

        # Encode to JPEG (quality ~85, adjust if you need smaller/larger)
        buf = io.BytesIO()
        Image.fromarray(frame).save(buf, format="JPEG", quality=85, optimize=True)
        jpeg_bytes = buf.getvalue()
        with cv:
            latest_jpeg = jpeg_bytes
            cv.notify_all()
        # tiny sleep to avoid pegging CPU if nothing is consuming
        time.sleep(0.01)

t = threading.Thread(target=capture_loop, daemon=True)
t.start()

# --- Web app ---
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
    with cv:
        if latest_jpeg is None:
            # block briefly for first frame
            cv.wait(timeout=1.0)
        data = latest_jpeg or b""
    return Response(data, mimetype="image/jpeg")

@app.route("/stream.mjpg")
def mjpeg():
    def gen():
        boundary = "--frame"
        # Send an initial frame quickly if we have one
        last = None
        while True:
            with cv:
                if latest_jpeg is None:
                    cv.wait(timeout=1.0)
                # Only push when we have a new frame
                if latest_jpeg is last:
                    cv.wait(timeout=0.05)
                data = latest_jpeg
                last = data
            if data is None:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n" +
                data + b"\r\n"
            )
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

def cleanup():
    global running
    running = False
    try:
        picam2.stop()
    except Exception:
        pass

if __name__ == "__main__":
    try:
        # 0.0.0.0 to serve on your LAN; change port if you like
        app.run(host="0.0.0.0", port=8000, threaded=True)
    finally:
        cleanup()
