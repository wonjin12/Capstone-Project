import json
from math import radians, cos, sin, asin, sqrt
from pathlib import Path

import pandas as pd


# =========================
# 경로 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output"

DONG_SUMMARY_CSV_PATH = OUTPUT_DIR / "dong_summary.csv"
SUBWAY_CSV_PATH = DATA_DIR / "subway_data.csv"

OUTPUT_CSV_PATH = OUTPUT_DIR / "dong_summary_with_subway.csv"
OUTPUT_JSON_PATH = OUTPUT_DIR / "dong_summary_with_subway.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# 거리 계산 함수
# =========================
def get_distance(lat1, lon1, lat2, lon2):
    """
    두 좌표 사이의 거리를 미터 단위로 계산
    """
    r = 6371000

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return r * c


# =========================
# 동 요약 데이터 로드
# =========================
def load_dong_summary() -> pd.DataFrame:
    df = pd.read_csv(DONG_SUMMARY_CSV_PATH, encoding="utf-8-sig")

    required_cols = ["gu", "dong", "center_lat", "center_lng"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"dong_summary.csv에 '{col}' 컬럼이 없습니다.")

    df["center_lat"] = pd.to_numeric(df["center_lat"], errors="coerce")
    df["center_lng"] = pd.to_numeric(df["center_lng"], errors="coerce")

    df = df.dropna(subset=["center_lat", "center_lng"]).copy()
    df["gu"] = df["gu"].astype(str).str.strip()
    df["dong"] = df["dong"].astype(str).str.strip()

    return df


# =========================
# 지하철 데이터 로드
# =========================
def load_subway_data() -> pd.DataFrame:
    cols = ["역한글명칭", "호선명칭", "환승역X좌표", "환승역Y좌표"]

    try:
        df = pd.read_csv(SUBWAY_CSV_PATH, usecols=cols, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(SUBWAY_CSV_PATH, usecols=cols, encoding="cp949")
        except UnicodeDecodeError:
            df = pd.read_csv(SUBWAY_CSV_PATH, usecols=cols, encoding="utf-8-sig")

    df = df.rename(columns={
        "역한글명칭": "station_name",
        "호선명칭": "line_name",
        "환승역X좌표": "lng",
        "환승역Y좌표": "lat"
    })

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")

    df = df.dropna(subset=["station_name", "line_name", "lat", "lng"]).copy()

    df["station_name"] = df["station_name"].astype(str).str.strip()
    df["line_name"] = df["line_name"].astype(str).str.strip()

    # 완전 중복 제거
    df = df.drop_duplicates(subset=["station_name", "line_name", "lat", "lng"]).reset_index(drop=True)

    return df


# =========================
# 지하철 접근성 계산
# =========================
def add_subway_features(dong_df: pd.DataFrame, subway_df: pd.DataFrame) -> pd.DataFrame:
    records = []

    for _, row in dong_df.iterrows():
        gu = row["gu"]
        dong = row["dong"]
        center_lat = float(row["center_lat"])
        center_lng = float(row["center_lng"])

        distances = []
        nearby_500_lines = set()
        nearby_1000_lines = set()

        for _, srow in subway_df.iterrows():
            dist = get_distance(
                center_lat,
                center_lng,
                float(srow["lat"]),
                float(srow["lng"])
            )

            distances.append((dist, srow["station_name"], srow["line_name"]))

            if dist <= 500:
                nearby_500_lines.add(srow["line_name"])
            if dist <= 1000:
                nearby_1000_lines.add(srow["line_name"])

        distances.sort(key=lambda x: x[0])

        if distances:
            nearest_station_distance = round(distances[0][0], 2)
            nearest_station_name = distances[0][1]
            nearest_station_line = distances[0][2]
        else:
            nearest_station_distance = None
            nearest_station_name = ""
            nearest_station_line = ""

        station_count_500m = sum(1 for d, _, _ in distances if d <= 500)
        station_count_1km = sum(1 for d, _, _ in distances if d <= 1000)

        line_count_500m = len([line for line in nearby_500_lines if line])
        line_count_1km = len([line for line in nearby_1000_lines if line])

        records.append({
            "gu": gu,
            "dong": dong,
            "nearest_station_distance": nearest_station_distance,
            "nearest_station_name": nearest_station_name,
            "nearest_station_line": nearest_station_line,
            "station_count_500m": station_count_500m,
            "station_count_1km": station_count_1km,
            "line_count_500m": line_count_500m,
            "line_count_1km": line_count_1km
        })

    subway_feature_df = pd.DataFrame(records)
    result = dong_df.merge(subway_feature_df, on=["gu", "dong"], how="left")

    return result


# =========================
# 저장
# =========================
def save_outputs(df: pd.DataFrame):
    df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")

    records = df.to_dict(orient="records")
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, allow_nan=False)


# =========================
# 메인 실행
# =========================
def main():
    print("dong_summary.csv 로드 중...")
    dong_df = load_dong_summary()
    print(f"동 데이터 수: {len(dong_df)}")

    print("subway_data.csv 로드 중...")
    subway_df = load_subway_data()
    print(f"지하철 데이터 수: {len(subway_df)}")

    print("동별 지하철 접근성 계산 중...")
    result_df = add_subway_features(dong_df, subway_df)

    print("미리보기:")
    print(result_df.head(10))

    print("파일 저장 중...")
    save_outputs(result_df)

    print("완료")
    print(f"CSV 저장 경로: {OUTPUT_CSV_PATH}")
    print(f"JSON 저장 경로: {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
