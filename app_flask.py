from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import re
import sys 
from pathlib import Path
import webbrowser

# =========================
# [중요] backend 폴더 내의 mapping_engine을 찾기 위한 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "backend"))

try:
    from mapping_engine import get_customized_conditions
except ImportError:
    print("Error: 'backend/mapping_engine.py'를 찾을 수 없습니다.")

app = Flask(__name__)
CORS(app)

# 경로 설정
INFRA_JSON_PATH = BASE_DIR / "output" / "dong_summary_with_subway.json"

def extract_keywords_from_message(message):
    """사용자 메시지에서 키워드 및 '역 이름' 추출"""
    mapping = {
        '지하철': ['역', '지하철', '교통', '전철', '역세권', '가깝'],
        '카페': ['카페', '커피', '까페', '디저트', '스벅', '투썸'],
        '병원': ['병원', '의료', '의사', '아플', '진료', '보건소'],
        '편의점': ['편의점', '마트', '24시', '편세권', '씨유', 'gs25'],
        '음식점': ['음식점', '맛집', '식당', '밥집', '먹거리', '회식']
    }
    
    # [1순위] 역 이름 추출 (간섭 방지를 위해 가장 먼저 실행)
    target_station = None
    # '역' 앞의 2~8자 한글을 찾고, '역'이라는 글자 자체를 제거하여 순수 지명만 추출
    station_match = re.search(r'([가-힣]{2,8})역', message)
    if station_match:
        target_station = station_match.group(1).replace("역", "").strip()

    # [2순위] 카테고리 키워드 추출
    found = []
    for key, synonyms in mapping.items():
        if any(sym in message for sym in synonyms):
            found.append(key)
            
    return found, target_station

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

        gu_dongs = [d for d in infra_data if target_gu in d.get('gu', '')]
        keywords, target_station = extract_keywords_from_message(user_message)
        conditions = get_customized_conditions(keywords, {})

        analysis_results = []
        for d in gu_dongs:
            # 기본 점수 시작
            score = 100.0
            
            # [역 이름 가산점] 유연한 매칭 로직 적용
            if target_station:
                # DB의 역 이름에서도 '역'을 떼고 순수 지명만 비교
                db_station_raw = d.get('nearest_station_name', '').strip()
                db_station_clean = db_station_raw.replace("역", "").strip()
                
                # 상호 포함 관계를 확인하여 매칭률 극대화 (예: '남영' == '남영')
                if target_station and db_station_clean:
                    if target_station in db_station_clean or db_station_clean in target_station:
                        score += 500.0
                        # 디버깅: 매칭 성공 시 서버 콘솔에 출력
                        print(f"Match Success: {d['dong']} with {target_station}")
            
            # [인프라별 가중치 합산]
            for key, cond in conditions.items():
                final_w = cond['final_w']
                radius = cond['radius']
                
                if '지하철' in key:
                    dist = d.get('nearest_station_distance', 2000)
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += d.get('subway_count', 0) * final_w * 15
                
                elif '카페' in key:
                    dist = d.get('nearest_cafe_distance', 500)
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += d.get('cafe_count', 0) * final_w * 5

                elif '병원' in key:
                    dist = d.get('nearest_hospital_distance', 1000)
                    h_count = d.get('hospital_count', d.get('medical_count', 0))
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += h_count * final_w * 10

                elif '편의점' in key:
                    # 필드명 대응: cvs, convenience 혼용 대응
                    dist = d.get('nearest_cvs_distance', d.get('nearest_convenience_distance', 300))
                    c_count = d.get('convenience_count', d.get('cvs_count', 0))
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += c_count * final_w * 15 # 편의점 가점 비중 상향 조정

                elif '음식점' in key:
                    dist = d.get('nearest_restaurant_distance', 400)
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += d.get('restaurant_count', 0) * final_w * 4

            analysis_results.append({
                "name": d.get('dong', '이름 없음'),
                "total": round(score, 1)
            })

        analysis_results.sort(key=lambda x: x['total'], reverse=True)
        top_5 = analysis_results[:5]

        return jsonify({"status": "success", "results": top_5})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    webbrowser.open("http://localhost:8501") 
    app.run(host='127.0.0.1', port=5000, debug=True)