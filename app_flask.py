#app_flask.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

from backend.mapping_engine import (run_recommendation)

app = Flask(__name__)
CORS(app)

# 데이터 파일 경로
INFRA_JSON_PATH = BASE_DIR / "data" / "dong_summary_with_subway.json"
SUBWAY_JSON_PATH = BASE_DIR / "html" / "subway_points.json"


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json

        user_message = data.get('message', '')
        
        raw_gu = data.get('gu', '').strip()
        target_gu = re.sub(r'구$', '', raw_gu).strip() 

        if not INFRA_JSON_PATH.exists():
            return jsonify({"status": "error", "message": "데이터 파일을 찾을 수 없습니다."})

        with open(INFRA_JSON_PATH, "r", encoding="utf-8") as f:
            infra_data = json.load(f)
            
        with open(SUBWAY_JSON_PATH, "r", encoding="utf-8") as f:
            subway_data = json.load(f)

        top_5 = run_recommendation(
                user_message,
                target_gu,
                infra_data,
                subway_data
            )

        return jsonify({"status": "success", "results": top_5})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)