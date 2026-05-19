from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import re
import sys 
from pathlib import Path
import webbrowser

# =========================
# 경로 및 환경 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "backend"))

try:
    from mapping_engine import get_customized_conditions
except ImportError:
    print("Error: 'backend/mapping_engine.py'를 찾을 수 없습니다.")

app = Flask(__name__)
CORS(app)

# 데이터 파일 경로
INFRA_JSON_PATH = BASE_DIR / "output" / "dong_summary_with_subway.json"

# =============================================================
# Flask-Streamlit 간의 행정동-법정동 매핑 사전 정의 (수궁동 및 구로구 추가)
# =============================================================
ADMIN_TO_LEGAL_DONG = {
    "신촌동": ["대현동", "대신동", "신촌동", "봉원동", "창천동"],
    "서강동": ["창전동", "상수동", "하중동", "신정동", "당인동"],
    "종로1.2.3.4가동": ["종로1가", "종로2가", "종로3가", "종로4가", "인사동", "낙원동", "피맛골", "청진동", "서린동", "수송동", "훈정동", "묘동", "봉익동", "돈의동", "장사동", "관수동", "관철동"],
    "종로5.6가동": ["종로5가", "종로6가", "연지동", "효제동"],
    "충현동": ["충정로2가", "충정로3가", "합동", "미근동", "북아현동"],
    "회현동": ["회현동1가", "회현동2가", "회현동3가", "남창동", "봉래동1가", "순화동"],
    "명동": ["명동1가", "명동2가", "충무로1가", "충무로2가", "저동1가", "삼각동", "수하동", "장교동", "수표동", "인현동1가", "예장동", "회현동2가"],
    "을지로동": ["을지로3가", "을지로4가", "을지로5가", "주교동", "방산동", "입정동", "산림동", "초동"],
    "소공동": ["소공동", "북창동", "태평로2가", "서소문동", "정동", "순화동", "의주로1가", "충정로1가"],
    "광희동": ["광희동1가", "광희동2가", "쌍림동", "을지로6가", "을지로7가", "오장동", "충무로4가", "충무로5가"],
    "필동": ["필동1가", "필동2가", "필동3가", "주자동", "예장동", "충무로3가"],
    "장충동": ["장충동1가", "장충동2가", "묵정동"],
    "수궁동": ["궁동", "온수동"],  # 👈 구로구 수궁동 매핑 추가 완료!
    "신도림동": ["신도림동"],  # 구로구 연계 추가
    "구로동": ["구로동"],  # 구로구 연계 추가
    "한강로동": ["한강로1가", "한강로2가", "한강로3가", "용산동3가", "용산동5가", "문배동", "신계동"],
    "혜화동": ["혜화동", "명륜1가", "명륜2가", "명륜3가", "명륜4가"]
}

def extract_keywords_from_message(message):
    """사용자 메시지에서 키워드, 역 이름, 그리고 명시적 '동' 이름 추출"""
    mapping = {
        '지하철': ['역', '지하철', '교통', '전철', '역세권', '가깝'],
        '카페': ['카페', '커피', '까페', '디저트', '스벅', '투썸'],
        '병원': ['병원', '의료', '의사', '아플', '진료', '보건소'],
        '편의점': ['편의점', '마트', '24시', '편세권', '씨유', 'gs25'],
        '음식점': ['음식점', '맛집', '식당', '밥집', '먹거리', '회식']
    }
    
    target_dong = None
    dong_match = re.search(r'([가-힣0-9]{2,5}동)', message)
    if dong_match:
        target_dong = dong_match.group(1).strip()

    target_station = None
    station_match = re.search(r'([가-힣]{2,8})역', message)
    if station_match:
        target_station = station_match.group(1).replace("역", "").strip()

    found = []
    for key, synonyms in mapping.items():
        if any(sym in message for sym in synonyms):
            found.append(key)
            
    return found, target_station, target_dong

def get_pure_dong_name(dong_name):
    """서울시 동네 이름을 순수 핵심 지명으로만 정형화"""
    if not dong_name:
        return ""
    name = dong_name.replace(" ", "")
    name = re.sub(r'(동|가)$', '', name)
    name = re.sub(r'[0-9]$', '', name)
    name = re.sub(r'(동|가)$', '', name)
    name = re.sub(r'[0-9]$', '', name)
    return name

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        raw_gu = data.get('gu', '').strip()
        target_gu = re.sub(r'구$', '', raw_gu).strip() 
        
        print(f"\n[로그] 프론트엔드 요청 구 원본: '{raw_gu}' -> 정제: '{target_gu}'")
        print(f"[로그] 유저 메시지: '{user_message}'")

        if not INFRA_JSON_PATH.exists():
            return jsonify({"status": "error", "message": "데이터 파일을 찾을 수 없습니다."})

        with open(INFRA_JSON_PATH, "r", encoding="utf-8") as f:
            infra_data = json.load(f)

        keywords, target_station, target_dong = extract_keywords_from_message(user_message)
        print(f"[로그] 추출된 텍스트 정보 -> 동: '{target_dong}', 역: '{target_station}'")
        
        if target_dong:
            pure_target = get_pure_dong_name(target_dong)
            for d in infra_data:
                pure_db = get_pure_dong_name(d.get('dong', ''))
                if pure_target and pure_db == pure_target:
                    db_gu_field = d.get('gu', '').strip()
                    if db_gu_field:
                        target_gu = re.sub(r'구$', '', db_gu_field).strip()
                        print(f"[로그] 동 이름 기반 구 역추적 성공! 타겟 구 변경 -> '{target_gu}'")
                        break

        gu_dongs = []
        target_gu_clean = target_gu + "구" if not target_gu.endswith("구") else target_gu
        target_gu_clean = target_gu_clean.replace(" ", "")
            
        for d in infra_data:
            db_gu_raw = d.get('gu', '').strip()
            if not db_gu_raw:
                continue
                
            db_gu_clean = db_gu_raw if db_gu_raw.endswith("구") else db_gu_raw + "구"
            db_gu_clean = db_gu_clean.replace(" ", "")
            
            if db_gu_clean == target_gu_clean:
                gu_dongs.append(d)
        
        print(f"[로그] 필터링된 해당 구('{target_gu_clean}')의 총 동네 개수: {len(gu_dongs)}개")

        conditions = get_customized_conditions(keywords, {})

        analysis_results = []
        for d in gu_dongs:
            score = 100.0
            db_dong_original = d.get('dong', '')
            
            if target_dong:
                pure_df_dong = get_pure_dong_name(db_dong_original)
                pure_target_dong = get_pure_dong_name(target_dong)
                
                is_direct_match = (pure_df_dong and pure_target_dong and (pure_df_dong == pure_target_dong))
                
                is_mapping_match = False
                if target_dong in ADMIN_TO_LEGAL_DONG:
                    if db_dong_original in ADMIN_TO_LEGAL_DONG[target_dong]:
                        is_mapping_match = True
                        
                if is_direct_match or is_mapping_match:
                    score += 5000.0
                    print(f"[로그] 가산점 폭탄 매칭 성공!! -> DB 동네: '{db_dong_original}' (+5000점)")
            
            if target_station:
                db_station_clean = d.get('nearest_station_name', '').replace("역", "").strip()
                if target_station in db_station_clean or db_station_clean in target_station:
                    score += 500.0
            
            for key, cond in conditions.items():
                final_w = cond.get('final_w', 1.0)
                radius = cond.get('radius', 1000)
                
                if '지하철' in key:
                    dist = d.get('nearest_station_distance', 2000)
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += d.get('station_count_500m', d.get('subway_count', 0)) * final_w * 20
                
                elif '카페' in key:
                    dist = d.get('nearest_cafe_distance', 500)
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += d.get('cafe_count', 0) * final_w * 5

                elif '병원' in key:
                    dist = d.get('nearest_hospital_distance', 1000)
                    h_count = d.get('medical_count', d.get('hospital_count', 0))
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += h_count * final_w * 10

                elif '편의점' in key:
                    dist = d.get('nearest_cvs_distance', 300)
                    c_count = d.get('convenience_count', d.get('cvs_count', 0))
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += c_count * final_w * 15

                elif '음식점' in key:
                    dist = d.get('nearest_restaurant_distance', 400)
                    if '_근접' in key and dist <= radius: score += (radius - dist) * final_w
                    elif '_밀도' in key: score += d.get('restaurant_count', 0) * final_w * 4

            res_gu = d.get('gu', raw_gu).strip()
            if not res_gu.endswith("구"):
                res_gu += "구"

            analysis_results.append({
                "name": db_dong_original,
                "total": round(score, 1),
                "gu": res_gu  
            })

        analysis_results.sort(key=lambda x: x['total'], reverse=True)
        top_5 = analysis_results[:5]
        
        print(f"[로그] 최종 추천 Top 5 결과 리스트:")
        for idx, item in enumerate(top_5):
            print(f"      {idx+1}등: {item['gu']} {item['name']} ({item['total']}점)")

        return jsonify({"status": "success", "results": top_5})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    webbrowser.open("http://localhost:8501") 
    app.run(host='127.0.0.1', port=5000, debug=True)