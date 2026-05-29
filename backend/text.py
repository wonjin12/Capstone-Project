#text.py

import re

# 키워드 추출
def extract_keywords_from_message(message):
    mapping = {
        '지하철_근접': ['역', '지하철', '교통', '전철', '역세권', '가깝'],
        '지하철_밀도' : ['지하철 많', '역 많', '지하철역이 많', '역이 많'],
        '지하철_환승' : ['환승', '노선','갈아타기'],
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
        target_station = station_match.group(1).strip()

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
