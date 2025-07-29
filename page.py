from flask import Flask, render_template

app = Flask(__name__)

@app.route('/home')
def index():
    services = [
        {"name": "로그인/회원가입", "manager": "이규연"},
        {"name": "계정", "manager": "이규연"},
        {"name": "병원", "manager": "이규연"},
        {"name": "리뷰", "manager": "남두현"},
        {"name": "예약", "manager": "남두현"},
        {"name": "의사", "manager": "남두현"},
        {"name": "패키지", "manager": "남두현"},
    ]
    return render_template('index.html', services=services)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)