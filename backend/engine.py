def get_customized_conditions(user_weights):
    # [시스템 기본 설정] 각 시설의 물리적 한계 거리(radius)와 중요도(base_w)
    base_config = {
        '음식점_근접': {'label': '맛집근접', 'radius': 300, 'base_w': 1.2},
        '음식점_밀도': {'label': '맛집상권', 'radius': 600, 'base_w': 1.0},

        '마트_근접': {'label': '마트근접', 'radius': 400, 'base_w': 1.1},
        '마트_밀도': {'label': '마트생활권', 'radius': 800, 'base_w': 0.9},

        '약국_근접': {'label': '약국근접', 'radius': 300, 'base_w': 1.2},
        '약국_밀도': {'label': '약국밀집', 'radius': 600, 'base_w': 1.0},

        '여가시설_근접': {'label': '여가근접', 'radius': 500, 'base_w': 1.0},
        '여가시설_밀도': {'label': '여가상권', 'radius': 1000, 'base_w': 0.8},

        '운동시설_근접': {'label': '운동근접', 'radius': 500, 'base_w': 1.0},
        '운동시설_밀도': {'label': '운동인프라', 'radius': 1000, 'base_w': 0.8},

        '학원_근접': {'label': '학원근접', 'radius': 400, 'base_w': 1.1},
        '학원_밀도': {'label': '교육인프라', 'radius': 800, 'base_w': 0.9},

        '미용실_근접': {'label': '미용근접', 'radius': 300, 'base_w': 1.0},
        '미용실_밀도': {'label': '미용상권', 'radius': 600, 'base_w': 0.8},

        '세탁소_근접': {'label': '세탁근접', 'radius': 300, 'base_w': 1.0},
        '세탁소_밀도': {'label': '세탁생활권', 'radius': 600, 'base_w': 0.8},

        '지하철역_근접': {'label': '지하철역근접', 'radius': 300, 'base_w': 1.0},
        '지하철역_밀도': {'label': '지하철역생활권', 'radius': 600, 'base_w': 0.8},
    }
    
    final_conditions = {}
    
    for key, user_w in user_weights.items():
        base_key = key.replace('_user', '')

        facility = base_key.split('_')[0]
        condition_type = base_key.split('_')[1]
        
        if base_key in base_config:
            final_w = round(base_config[base_key]['base_w'] * user_w, 2)

            final_conditions[base_key] = {
                'label': base_config[base_key]['label'],
                'radius': base_config[base_key]['radius'],
                'final_w': final_w,
                'facility': facility,       
                'type': condition_type
            }

    return final_conditions