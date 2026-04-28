# mapping_engine.py

def get_customized_conditions(keywords, user_weights):
    """
    Kiwi 인터페이스에서 분석된 8개 세부 항목별 가중치를 반영합니다.
    """
    # [시스템 기본 설정] 각 시설의 물리적 한계 거리(radius)와 중요도(base_w)
    base_config = {
        '지하철_근접': {'label': '초역세권(도보)', 'radius': 400, 'base_w': 1.8},
        '지하철_밀도': {'label': '다세권(노선)', 'radius': 800, 'base_w': 1.2},
        
        '카페_근접': {'label': '홈카페(단지내)', 'radius': 200, 'base_w': 1.1},
        '카페_밀도': {'label': '카세권(상권)', 'radius': 400, 'base_w': 0.9},
        
        '병원_근접': {'label': '응급권(도보)', 'radius': 500, 'base_w': 1.3},
        '병원_밀도': {'label': '의세권(인프라)', 'radius': 1000, 'base_w': 1.0},
        
        '편의점_근접': {'label': '슬세권(초근접)', 'radius': 150, 'base_w': 1.4},
        '편의점_밀도': {'label': '편세권(생활편의)', 'radius': 300, 'base_w': 1.1}
    }
    
    final_conditions = {}
    
    for kw in keywords:
        for suffix in ['_근접', '_밀도']:
            key = kw + suffix
            if key in base_config:
                # [중요] Kiwi가 추출한 '항목_유형_user' 가중치를 가져옴 (없으면 기본 1.0)
                user_w = user_weights.get(f"{key}_user", 1.0)
                
                # 최종 가중치 계산
                final_w = round(base_config[key]['base_w'] * user_w, 2)
                
                final_conditions[key] = {
                    'label': base_config[key]['label'],
                    'radius': base_config[key]['radius'],
                    'final_w': final_w
                }
                
    return final_conditions