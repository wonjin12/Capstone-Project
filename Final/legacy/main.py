# main.py

import pandas as pd

try:
    import legacy.engine as engine
except ModuleNotFoundError:
    import legacy.engine as engine


# 🔵 dataset 로드
dataset_df = pd.read_csv(
    "data/dataset.csv",
    encoding="utf-8"
)

# 🔵 (가정) 동→구 매핑 파일
dong_map_df = pd.read_csv(
    "data/dong_to_gu.csv",
    encoding="utf-8"
)

# 🔵 dataset + 구 정보 결합
merged_df = pd.merge(
    dataset_df,
    dong_map_df,
    on="행정동명"
)



def run_analysis(target_gu, user_prefs):


    conditions = engine.get_customized_conditions(
        user_prefs
    )

    results = []

    # 🔵 입력한 구만 필터
    gu_filtered = merged_df[
        merged_df["구"] == target_gu
    ]
    print(gu_filtered.head())

    if gu_filtered.empty:
        return []

    # 🔵 동별 점수 계산
    for _, row in gu_filtered.iterrows():

        dong_name = row["행정동명"]

        total_score = 0

        for condition, info in conditions.items():

            facility = info['facility']   # kiwi에서 만든 거
            weight = info['final_w']

            if weight <= 1.0:
                continue

            if facility not in row:
                continue

            count = row[facility]

            total_score += count * weight

        total_score = round(total_score, 2)
        
        results.append({
            "name": dong_name,
            "total": total_score
        })


    # 🔵 점수 정렬
    results.sort(
        key=lambda x: x["total"],
        reverse=True
    )

    # 🔵 상위 5개 반환
    return results[:5]