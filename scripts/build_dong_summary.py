import json
from pathlib import Path

import pandas as pd


# =========================
# 경로 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output"

SHOP_PATH = DATA_DIR / "seoul_shop_data.csv"
OUTPUT_CSV_PATH = OUTPUT_DIR / "dong_summary.csv"
OUTPUT_JSON_PATH = OUTPUT_DIR / "dong_summary.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# 업종 세분화 분류
# =========================
def classify_category(raw_category: str) -> str:
    """
    상권업종소분류명을 프로젝트용 범주로 세분화
    """
    if pd.isna(raw_category):
        return "기타"

    text = str(raw_category).strip()

    # 1. 카페
    if (
        "카페" in text or
        "커피" in text or
        "디저트" in text or
        "베이커리" in text
    ):
        return "카페"

    # 2. 음식점
    elif (
        "음식" in text or
        "식당" in text or
        "한식" in text or
        "중식" in text or
        "일식" in text or
        "양식" in text or
        "분식" in text or
        "치킨" in text or
        "피자" in text or
        "햄버거" in text or
        "패스트푸드" in text or
        "족발" in text or
        "보쌈" in text or
        "고기" in text or
        "국수" in text or
        "죽" in text or
        "도시락" in text
    ):
        return "음식점"

    # 3. 편의시설
    elif (
        "편의점" in text or
        "마트" in text or
        "슈퍼" in text or
        "생활용품" in text or
        "잡화" in text
    ):
        return "편의시설"

    # 4. 의료
    elif (
        "병원" in text or
        "의원" in text or
        "치과" in text or
        "한의원" in text or
        "약국" in text or
        "의료" in text
    ):
        return "의료"

    # 5. 금융
    elif (
        "은행" in text or
        "금융" in text or
        "보험" in text or
        "증권" in text or
        "atm" in text.lower()
    ):
        return "금융"

    # 6. 교육
    elif (
        "학원" in text or
        "교습" in text or
        "독서실" in text or
        "스터디" in text or
        "교육" in text
    ):
        return "교육"

    # 7. 생활서비스
    elif (
        "미용" in text or
        "헤어" in text or
        "네일" in text or
        "피부관리" in text or
        "세탁" in text or
        "수선" in text or
        "사진" in text or
        "청소" in text or
        "부동산" in text
    ):
        return "생활서비스"

    # 8. 문화여가
    elif (
        "헬스" in text or
        "체육" in text or
        "필라테스" in text or
        "요가" in text or
        "골프" in text or
        "영화" in text or
        "공연" in text or
        "노래방" in text or
        "pc방" in text.lower() or
        "오락" in text
    ):
        return "문화여가"

    # 9. 기타
    else:
        return "기타"


# =========================
# 상권 데이터 로드
# =========================
def load_shop_data() -> pd.DataFrame:
    cols = ["상호명", "상권업종소분류명", "시군구명", "행정동명", "경도", "위도"]

    try:
        df = pd.read_csv(
            SHOP_PATH,
            header=1,
            usecols=cols,
            encoding="cp949"
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            SHOP_PATH,
            header=1,
            usecols=cols,
            encoding="utf-8-sig"
        )

    df = df.rename(columns={
        "상호명": "name",
        "상권업종소분류명": "category_raw",
        "시군구명": "gu",
        "행정동명": "dong",
        "위도": "lat",
        "경도": "lng"
    })

    # 숫자형 변환
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")

    # 결측 제거
    df = df.dropna(subset=["gu", "dong", "lat", "lng"]).copy()

    # 문자열 정리
    df["gu"] = df["gu"].astype(str).str.strip()
    df["dong"] = df["dong"].astype(str).str.strip()
    df["category_group"] = df["category_raw"].apply(classify_category)

    return df


# =========================
# 동 단위 요약 생성
# =========================
def build_dong_summary(df: pd.DataFrame) -> pd.DataFrame:
    # 1) 동 대표 좌표 + 전체 상권 수
    summary = (
        df.groupby(["gu", "dong"], as_index=False)
        .agg(
            center_lat=("lat", "mean"),
            center_lng=("lng", "mean"),
            total_shop_count=("name", "count")
        )
    )

    # 2) 카테고리별 개수 pivot
    category_counts = (
        df.pivot_table(
            index=["gu", "dong"],
            columns="category_group",
            values="name",
            aggfunc="count",
            fill_value=0
        )
        .reset_index()
    )

    result = summary.merge(category_counts, on=["gu", "dong"], how="left")

    # 컬럼 누락 대비
    for col in ["카페", "음식점", "편의시설", "의료", "금융", "교육", "생활서비스", "문화여가", "기타"]:
        if col not in result.columns:
            result[col] = 0

    # 컬럼명 변경
    result = result.rename(columns={
        "카페": "cafe_count",
        "음식점": "restaurant_count",
        "편의시설": "convenience_count",
        "의료": "medical_count",
        "금융": "finance_count",
        "교육": "education_count",
        "생활서비스": "living_service_count",
        "문화여가": "leisure_count",
        "기타": "etc_count"
    })

    # 생활 인프라 합계
    result["life_infra_count"] = (
        result["convenience_count"]
        + result["medical_count"]
        + result["finance_count"]
        + result["education_count"]
        + result["living_service_count"]
        + result["restaurant_count"]
    )

    # 대표 좌표 반올림
    result["center_lat"] = result["center_lat"].round(6)
    result["center_lng"] = result["center_lng"].round(6)

    # 정렬
    result = result.sort_values(["gu", "dong"]).reset_index(drop=True)

    return result


# =========================
# 저장
# =========================
def save_outputs(df: pd.DataFrame) -> None:
    df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")

    records = df.to_dict(orient="records")
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, allow_nan=False)


# =========================
# 메인 실행
# =========================
def main():
    print("상권 데이터 로드 중...")
    shop_df = load_shop_data()
    print(f"원본 데이터 수: {len(shop_df)}")

    print("동 단위 요약 생성 중...")
    dong_summary = build_dong_summary(shop_df)

    print(f"생성된 동 수: {len(dong_summary)}")
    print(dong_summary.head(10))

    print("파일 저장 중...")
    save_outputs(dong_summary)

    print("완료")
    print(f"CSV 저장 경로: {OUTPUT_CSV_PATH}")
    print(f"JSON 저장 경로: {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
