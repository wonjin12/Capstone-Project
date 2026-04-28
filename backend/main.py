# main.py

import pandas as pd

try:
    import backend.mapping_engine as mapping_engine
except ModuleNotFoundError:
    import mapping_engine


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

    keywords = ['지하철', '카페', '병원', '편의점']

    conditions = mapping_engine.get_customized_conditions(
        keywords,
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

        for kw in keywords:

            d_key = f"{kw}_밀도"

            if d_key not in conditions:
                continue

            # 🔵 컬럼 정확히 반영
            if kw == "지하철":
                count = row["지하철역"]

            elif kw == "카페":
                count = row["카페"]

            elif kw == "병원":
                count = row["병원"]

            elif kw == "편의점":
                count = row["편의점"]

            else:
                count = 0

            total_score += (
                count *
                conditions[d_key]["final_w"]
            )

        results.append({
            "name": dong_name,
            "total": round(total_score, 2)
        })

    # 🔵 점수 정렬
    results.sort(
        key=lambda x: x["total"],
        reverse=True
    )

    # 🔵 상위 5개 반환
    return results[:5]