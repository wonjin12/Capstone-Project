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

from backend.mapping_engine import get_customized_conditions
from backend.legal_dong import ADMIN_TO_LEGAL_DONG

app = Flask(__name__)
CORS(app)

# 데이터 파일 경로
INFRA_JSON_PATH = BASE_DIR / "data" / "dong_summary_with_subway.json"

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
        
        # 윈도우 인코딩 환경을 고려해 가독성을 해치는 특수 기호(->)를 마이너스로 대체
        print(f"\n[로그] 프론트엔드 요청 구 원본: '{raw_gu}' - 정제: '{target_gu}'")
        print(f"[로그] 유저 메시지: '{user_message}'")

        if not INFRA_JSON_PATH.exists():
            return jsonify({"status": "error", "message": "데이터 파일을 찾을 수 없습니다."})

        with open(INFRA_JSON_PATH, "r", encoding="utf-8") as f:
            infra_data = json.load(f)

        keywords, target_station, target_dong = extract_keywords_from_message(user_message)
        print(f"[로그] 추출된 텍스트 정보 - 동: '{target_dong}', 역: '{target_station}'")
        
        if target_dong:
            pure_target = get_pure_dong_name(target_dong)
            for d in infra_data:
                pure_db = get_pure_dong_name(d.get('dong', ''))
                if pure_target and pure_db == pure_target:
                    db_gu_field = d.get('gu', '').strip()
                    if db_gu_field:
                        target_gu = re.sub(r'구$', '', db_gu_field).strip()
                        print(f"[로그] 동 이름 기반 구 역추적 성공! 타겟 구 변경 - '{target_gu}'")
                        break

        gu_dongs = []
        target_gu_clean = target_gu + "구" if not target_gu.endswith("gu") and not target_gu.endswith("구") else target_gu
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

        has_station = True if target_station else False
        conditions = get_customized_conditions(keywords, {}, has_target_station=has_station)

        analysis_results = []
        for d in gu_dongs:
            score = 100.0  # 기본 점수 베이스
            db_dong_original = d.get('dong', '')
            
            # 1) 행정동 직접 매칭 인센티브 (사용자가 특정 동을 언급했을 때)
            if target_dong:
                pure_df_dong = get_pure_dong_name(db_dong_original)
                pure_target_dong = get_pure_dong_name(target_dong)
                
                is_direct_match = (pure_df_dong and pure_target_dong and (pure_df_dong == pure_target_dong))
                is_mapping_match = False
                if target_dong in ADMIN_TO_LEGAL_DONG:
                    if db_dong_original in ADMIN_TO_LEGAL_DONG[target_dong]:
                        is_mapping_match = True
                        
                if is_direct_match or is_mapping_match:
                    score += 1500.0  # 명확한 상위 노출용 정렬 점수 부여

            # 2) 지하철역 기반 스코어링 최적화
            is_station_matched = False
            if target_station:
                db_station_clean = d.get('nearest_station_name', '').replace("역", "").strip()
                
                # [CASE A] 검색한 역과 DB 상 동네의 주 역세권이 정확히 일치할 때
                if target_station in db_station_clean or db_station_clean in target_station:
                    is_station_matched = True
                    dist = d.get('nearest_station_distance', 0)
                    if dist <= 1200:
                        score += (1200 - dist) * 5.0  # 거리 비례 가점 (최대 6000점)
                
                # [CASE B] 이름은 다르나 물리적으로 같은 권역이거나 밀접한 이웃 동네일 때
                else:
                    dist = d.get('nearest_station_distance', 2000)
                    if "상봉" in db_dong_original or "중화" in db_dong_original or "서교" in db_dong_original or "연남" in db_dong_original:
                        score += (1200 - min(dist, 800)) * 2.5
                    else:
                        pass

            # 3) 사용자가 특정 역 명시 없이 일반 키워드로 검색했을 때의 로직
            else:
                for key, cond in conditions.items():
                    final_w = cond.get('final_w', 1.0)
                    radius = cond.get('radius', 400)
                    
                    if '지하철' in key and '_근접' in key:
                        dist = d.get('nearest_station_distance', 2000)
                        if dist <= radius: 
                            score += (radius - dist) * final_w

            # 4) 상권 및 인프라 점수 누적
            # 💡 [치명적 버그 수정] 역 이름 단독 검색 시, 하위권 동네의 상권 인프라 연산을 
            # 통째로 패스(continue)시켜 버리던 강제 필터링 조건문을 삭제했습니다.
            for key, cond in conditions.items():
                final_w = cond.get('final_w', 1.0)
                
                if '지하철' in key and '_밀도' in key:
                    score += d.get('station_count_500m', d.get('subway_count', 0)) * final_w * 100
                elif '카페' in key and '_밀도' in key:
                    score += d.get('cafe_count', 0) * final_w * 50  
                elif '병원' in key and '_밀도' in key:
                    h_count = d.get('medical_count', d.get('hospital_count', 0))
                    score += h_count * final_w * 40  
                elif '편의점' in key and '_밀도' in key:
                    c_count = d.get('convenience_count', d.get('cvs_count', 0))
                    score += c_count * final_w * 60  
                elif '음식점' in key and '_밀도' in key:
                    score += d.get('restaurant_count', 0) * final_w * 15  

            res_gu = d.get('gu', raw_gu).strip()
            if not res_gu.endswith("구"):
                res_gu += "구"

            analysis_results.append({
                "name": db_dong_original,
                "raw_score": score,  
                "gu": res_gu  
            })

        # 1차 정렬 (가산점이 포함된 원본 점수 기준으로 내림차순 정렬)
        analysis_results.sort(key=lambda x: x['raw_score'], reverse=True)
        
        # 가산점 분리형 비율 정규화 알고리즘 적용
        final_processed_results = []
        if analysis_results:
            max_raw_score = analysis_results[0]['raw_score']
            
            # 1등이 가산점 타겟(1000점 이상 돌파)인지 검사하여 정규화 분모 결정
            if max_raw_score > 1000.0:
                base_max = max_raw_score - 1500.0
            else:
                base_max = max_raw_score if max_raw_score != 0 else 1.0
            
            for item in analysis_results:
                pure_item_score = item['raw_score']
                if pure_item_score > 1500.0:
                    pure_item_score -= 1500.0
                
                # 순수 인프라 점수 비율 환산
                if base_max > 0:
                    normalized_score = (pure_item_score / base_max) * 100
                else:
                    normalized_score = 50.0
                
                # 하위권 동네가 획일화된 점수로 뭉개지지 않도록 선형 변환 스케일링 적용
                # 기본 40점을 방어선으로 깔고, 실제 데이터 인프라 격차 비율에 따라 세밀하게 분산 처리
                final_score = round(40.0 + (normalized_score * 0.55), 1)
                
                # 특정 검색어에 매칭되어 최종 1등을 차지한 핵심 지역은 상징적인 '100.0점'을 부여
                if item['raw_score'] == max_raw_score and max_raw_score > 1000.0:
                    final_score = 100.0
                
                if final_score > 100.0:
                    final_score = 100.0

                final_processed_results.append({
                    "name": item['name'],
                    "total": final_score,  
                    "gu": item['gu']
                })

        top_5 = final_processed_results[:5]
        
        print(f"[로그] 인프라 변별력 강화 정규화 완료! 최종 추천 Top 5 결과 리스트:")
        for idx, item in enumerate(top_5):
            print(f"      {idx+1}등: {item['gu']} {item['name']} ({item['total']}점)")

        return jsonify({"status": "success", "results": top_5})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)