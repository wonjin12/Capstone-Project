# mapping_engine.py

def get_customized_conditions(keywords, user_weights, has_target_station=False):
    """
    Kiwi 인터페이스에서 분석된 10개 세부 항목별 가중치를 반영합니다.
    💡 특정 역 검색 시(has_target_station=True) 지하철 도보 영향권(radius)을 1200m로 확장하여 
       물리적으로 인접한 이웃 동네들이 정상적인 거리 점수를 획득할 수 있도록 구조를 보정합니다.
    """
    # [시스템 기본 설정] 각 시설의 물리적 한계 거리(radius)와 중요도(base_w)
    # 특정 역 중심 검색일 때는 지하철 근접 반경을 400m에서 1200m로 동적 확장합니다.
    subway_radius = 1200 if has_target_station else 400
    
    base_config = {
        '지하철_근접': {'label': '초역세권(도보)', 'radius': subway_radius, 'base_w': 5.0},
        '지하철_밀도': {'label': '다세권(노선)', 'radius': 800, 'base_w': 1.2},
        
        '카페_밀도': {'label': '카세권(상권)', 'radius': 400, 'base_w': 0.5},
        
        '병원_밀도': {'label': '의세권(인프라)', 'radius': 1000, 'base_w': 0.5},
        
        '편의점_밀도': {'label': '편세권(생활편의)', 'radius': 300, 'base_w': 0.5},

        '음식점_밀도': {'label': '먹세권(상권)', 'radius': 500, 'base_w': 0.5}
    }
    
    final_conditions = {}
    
    for kw in keywords:
        for suffix in ['_근접', '_밀도']:
            key = kw + suffix
            if key in base_config:
                # Kiwi 가중치 (없으면 기본 1.0)
                user_w = user_weights.get(f"{key}_user", 1.0)
                
                final_w = round(base_config[key]['base_w'] * user_w, 2)
                
                final_conditions[key] = {
                    'label': base_config[key]['label'],
                    'radius': base_config[key]['radius'],
                    'final_w': final_w
                }
                
    return final_conditions