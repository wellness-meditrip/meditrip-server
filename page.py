from flask import Flask, render_template
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

@app.route('/home')
def index():
    base_url = os.getenv('BASE_URL', 'http://localhost')
    doctor_port = os.getenv('DOCTOR_SERVICE_PORT')
    chatbot_port = os.getenv('CHATBOT_SERVICE_PORT')
    
    services = [
        {"name": "로그인/회원가입", "manager": "이규연", "docs": "개발중"},
        {"name": "계정", "manager": "이규연", "docs": "개발중"},
        {"name": "병원", "manager": "이규연", "docs": "개발중"},
        {"name": "패키지", "manager": "이규연", "docs": "개발중"},
        {"name": "리뷰", "manager": "남두현", "docs": "개발중"},
        {"name": "예약", "manager": "남두현", "docs": "개발중"},
        {"name": " 의사", "manager": "남두현", "docs": f'<a href="{base_url}:{doctor_port}/docs" target="_blank">API 문서</a>'},
        {"name": " 챗봇", "manager": "남두현", "docs": f'<a href="{base_url}:{chatbot_port}/docs" target="_blank">API 문서</a>'},
    ]
    return render_template('index.html', services=services)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)