#mapping_engine.py
from backend.legal_dong import (ADMIN_TO_LEGAL_DONG)
from backend.score_engine import (calculate_dong_score)
from backend.text import (extract_keywords_from_message)

from math import radians, sin, cos, sqrt, atan2


def get_customized_conditions(keywords):

    final_conditions = {}

    for kw in keywords:

        final_conditions[kw] = {
            'final_w': 1.0
        }

    return final_conditions

def normalize_station_name(name):

    return (
        name
        .replace("역", "")
        .split("(")[0]
        .strip()
    )


# 역 좌표 찾기 함수
def find_station_coords(station_name, subway_data):

    target = normalize_station_name(station_name)

    for station in subway_data:

        db_name = normalize_station_name(
            station['name']
        )

        if db_name == target:

            return (
                station['lat'],
                station['lng']
            )

    return None

def calculate_distance(lat1, lng1, lat2, lng2):

    R = 6371  # 지구 반지름 (km)

    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlng / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

def filter_dongs_by_station(
    gu_dongs,
    target_station,
    subway_data
):
    
    print("[target_station]", target_station)

    if not target_station:
        return gu_dongs

    station_coords = find_station_coords(
        target_station,
        subway_data
    )


    if not station_coords:
        return gu_dongs

    station_lat, station_lng = station_coords

    filtered_dongs = []

    for d in gu_dongs:

        dong_lat = d.get('center_lat')
        dong_lng = d.get('center_lng')

        if dong_lat is None or dong_lng is None:
            continue

        distance = calculate_distance(
            dong_lat,
            dong_lng,
            station_lat,
            station_lng
        )

        d['target_station_distance'] = distance

        filtered_dongs.append(d)

    filtered_dongs.sort(
        key=lambda x: x.get(
            'target_station_distance',
            9999
        )
    )

    return filtered_dongs

def run_recommendation(
        user_message,
        target_gu,
        infra_data,
        subway_data):

    print("추천 시작")

    keywords, target_station, target_dong = extract_keywords_from_message(user_message)
    conditions = get_customized_conditions(keywords)

    gu_dongs = filter_gu_dongs(
        infra_data,
        target_gu
    )

    # 특정 역 기준 후보
    filtered_dongs = []

    filtered_dongs = filter_dongs_by_station(
        gu_dongs,
        target_station,
        subway_data
    )
    
    analysis_results = []



    infra_map = {
        '카페' : 'cafe_count',
        '병원' : 'medical_count',
        '편의점' : 'convenience_count',
        '음식점': 'restaurant_count',
        '지하철_밀도' : 'station_count_500m',
        '지하철_환승' : 'line_count_500m'
        }
        

    for d in filtered_dongs:

        score = calculate_dong_score(
            d,
            filtered_dongs,
            gu_dongs,
            target_dong,
            conditions,
            infra_map,
            ADMIN_TO_LEGAL_DONG
            )

        db_dong_original = d.get('dong', '')

        res_gu = d.get('gu', target_gu).strip()
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

            
    print(f"[로그] 추출된 텍스트 정보 -> 동: '{target_dong}', 역: '{target_station}'")


    return top_5



def filter_gu_dongs(infra_data, target_gu):

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

        return gu_dongs

