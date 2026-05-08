from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import re
import sys  # [추가] 경로 인식을 위해 필요
from pathlib import Path
import webbrowser

# =========================
# [중요] backend 폴더 내의 mapping_engine을 찾기 위한 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent
# backend 폴더를 파이썬이 찾을 수 있는 경로 리스트에 추가합니다.
sys.path.append(str(BASE_DIR / "backend"))

try:
    from mapping_engine import get_customized_conditions
except ImportError:
    print("Error: 'backend/mapping_engine.py'를 찾을 수 없습니다. 폴더명을 확인해 주세요.")

app = Flask(__name__)
CORS(app)

# 경로 설정
INFRA_JSON_PATH = BASE_DIR / "output" / "dong_summary_with_subway.json"

def extract_keywords_from_message(message):
    """사용자 메시지에서 분석 대상 키워드 추출"""
    mapping = {
        '지하철': ['역', '지하철', '교통', '전철', '역세권', '가깝'],
        '카페': ['카페', '커피', '까페', '디저트', '스벅', '투썸'],
        '병원': ['병원', '의료', '의사', '아플', '진료', '보건소'],
        '편의점': ['편의점', '마트', '24시', '편세권', '씨유', 'gs25']
    }
    found = []
    for key, synonyms in mapping.items():
        if any(sym in message for sym in synonyms):
            found.append(key)
    return found

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        target_gu = data.get('gu', '').replace("구", "").strip()
        
        if not INFRA_JSON_PATH.exists():
            return jsonify({"status": "error", "message": "데이터 파일을 찾을 수 없습니다."})

        with open(INFRA_JSON_PATH, "r", encoding="utf-8") as f:
            infra_data = json.load(f)

        # 1. 해당 '구' 필터링
        gu_dongs = [d for d in infra_data if target_gu in d.get('gu', '')]

        # 2. 키워드 추출 및 mapping_engine 가중치 가져오기
        keywords = extract_keywords_from_message(user_message)
        # 현재는 사용자 개별 가중치(user_weights)가 없으므로 빈 딕셔너리 전달
        conditions = get_customized_conditions(keywords, {})

        analysis_results = []
        for d in gu_dongs:
            # 기본 점수 100점 시작
            score = 100.0
            
            # [가중치 계산 로직] mapping_engine의 반경(radius)과 가중치(final_w)를 활용
            for key, cond in conditions.items():
                final_w = cond['final_w']
                radius = cond['radius']
                
                # --- 지하철 (Subway) ---
                if '지하철' in key:
                    dist = d.get('nearest_station_distance', 2000)
                    if '_근접' in key and dist <= radius:
                        score += (radius - dist) * final_w  # 가까울수록 가산점
                    elif '_밀도' in key:
                        score += d.get('subway_count', 0) * final_w * 15 # 노선 개수 점수
                
                # --- 카페 (Cafe) ---
                elif '카페' in key:
                    if '_근접' in key:
                        # 데이터에 카페 거리가 없을 경우를 대비해 500m 기본값 설정
                        dist = d.get('nearest_cafe_distance', 500)
                        if dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key:
                        score += d.get('cafe_count', 0) * final_w * 5

                # --- 병원 (Hospital) ---
                elif '병원' in key:
                    if '_근접' in key:
                        dist = d.get('nearest_hospital_distance', 1000)
                        if dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key:
                        score += d.get('hospital_count', 0) * final_w * 10

                # --- 편의점 (CVS) ---
                elif '편의점' in key:
                    if '_근접' in key:
                        dist = d.get('nearest_cvs_distance', 300)
                        if dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key:
                        score += d.get('convenience_count', 0) * final_w * 3

            analysis_results.append({
                "name": d.get('dong', '이름 없음'),
                "total": round(score, 1)
            })

        # 3. 결과 정렬 (높은 점수순)
        analysis_results.sort(key=lambda x: x['total'], reverse=True)
        top_5 = analysis_results[:5]

        return jsonify({"status": "success", "results": top_5})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Streamlit 자동 오픈
    webbrowser.open("http://localhost:8501") 
    app.run(host='127.0.0.1', port=5000, debug=True)