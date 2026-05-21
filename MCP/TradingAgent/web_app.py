from flask import Flask, render_template
from database_manager import DatabaseManager
import json

app = Flask(__name__)
db = DatabaseManager()

@app.route('/')
def dashboard():
    logs = db.get_logs(limit=20)
    # JSON 문자열을 파이썬 객체로 변환 (표시용)
    for log in logs:
        if isinstance(log['market_data'], str):
            log['market_data'] = json.loads(log['market_data'])
        if isinstance(log['raw_response'], str):
            log['raw_response'] = json.loads(log['raw_response'])
    return render_template('dashboard.html', logs=logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
