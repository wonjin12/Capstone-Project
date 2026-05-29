#score_engine.py

from backend.text import (get_pure_dong_name)

def calculate_dong_score(
    d,
    filtered_dongs,
    gu_dongs,
    target_dong,
    conditions,
    infra_map,
    ADMIN_TO_LEGAL_DONG
):


    score = 0
        
    db_dong_original = d.get('dong', '')
            
    if target_dong:
                
        pure_df_dong = get_pure_dong_name(db_dong_original)
        pure_target_dong = get_pure_dong_name(target_dong)
                
        is_direct_match = (
            pure_df_dong and 
            pure_target_dong and 
            (pure_df_dong == pure_target_dong)
        )
                
        is_mapping_match = False
        if target_dong in ADMIN_TO_LEGAL_DONG:
                    
            if db_dong_original in ADMIN_TO_LEGAL_DONG[target_dong]:
                is_mapping_match = True
                        
            if is_direct_match or is_mapping_match:
                score *= 1.3
            
    for key, cond in conditions.items():
            
        final_w = cond.get('final_w', 1.0)
            
        if '지하철_근접' in key:

            max_dist = max(
                x.get('target_station_distance', 9999)
                for x in filtered_dongs
            )

            dist = d.get('target_station_distance', 9999)

            subway_score = (
                1 - (dist / max_dist)
                if max_dist > 0 else 0
            )

            score += subway_score * 100
        

        for infra_name, db_column in infra_map.items():

                if infra_name in key:

                    current_value = d.get(db_column, 0)

                    max_value = max(
                            x.get(db_column, 0)
                        for x in gu_dongs
                    )

                    normalized_score = (
                        current_value / max_value
                        if max_value > 0 else 0
                    )

                    score += normalized_score * 100 * final_w

                    condition_count = len(conditions)

                    if condition_count > 0:
                        score = score / condition_count


        return round(score, 1)
    