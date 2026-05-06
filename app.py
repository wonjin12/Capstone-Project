from pathlib import Path
import pandas as pd
import streamlit as st


# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="서울시 실거래가 매물 검색",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 서울시 실거래가 매물 검색")
st.caption("선택된 동 기준으로 주택유형, 거래유형, 보증금/월세 범위를 설정해 실거래가 결과를 확인합니다.")


# =========================
# 파일 경로
# =========================
current_dir = Path(__file__).parent
transaction_path = current_dir / "data" / "transaction_unified.csv"

# =========================
# 데이터 로드
# =========================
@st.cache_data
def load_transaction_data(file_path: Path) -> pd.DataFrame:
    df = pd.read_csv(file_path, encoding="utf-8-sig")

    for col in ["deposit", "monthly_rent", "area_m2", "floor"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["gu", "dong", "property_type", "rent_type", "address", "complex_name"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def map_property_type(user_input: str) -> str:
    mapping = {
        "아파트": "아파트",
        "주택": "단독다가구",
        "빌라": "연립다세대",
        "오피스텔": "오피스텔"
    }
    return mapping.get(user_input.strip(), user_input.strip())


def reverse_property_type(internal_value: str) -> str:
    mapping = {
        "아파트": "아파트",
        "단독다가구": "주택",
        "연립다세대": "빌라",
        "오피스텔": "오피스텔"
    }
    return mapping.get(internal_value, internal_value)


def format_money(value):
    if pd.isna(value):
        return "-"
    return f"{int(value):,}만원"


def format_area(value):
    if pd.isna(value):
        return "-"
    return f"{value:.1f}㎡"


def format_floor(value):
    if pd.isna(value):
        return "-"
    return f"{int(value)}층"


def make_display_table(df: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame()
    result["주소"] = df["address"]
    result["단지명"] = df["complex_name"].replace("", "-")
    result["거래유형"] = df["rent_type"]
    result["보증금"] = df["deposit"].apply(format_money)
    result["월세"] = df.apply(
        lambda row: "-" if row["rent_type"] == "전세" else format_money(row["monthly_rent"]),
        axis=1
    )
    result["면적"] = df["area_m2"].apply(format_area)
    result["층"] = df["floor"].apply(format_floor)
    return result


# =========================
# 데이터 준비
# =========================
if not transaction_path.exists():
    st.error(f"파일이 없습니다: {transaction_path}")
    st.stop()

df = load_transaction_data(transaction_path)

if df.empty:
    st.error("실거래가 데이터가 비어 있습니다.")
    st.stop()


# =========================
# 동 선택
# =========================
dong_list = sorted([d for d in df["dong"].dropna().unique().tolist() if str(d).strip() != ""])

selected_dong = st.selectbox(
    "동을 선택해주세요",
    options=dong_list,
    index=0 if dong_list else None
)

dong_df = df[df["dong"] == selected_dong].copy()

if dong_df.empty:
    st.warning("선택한 동의 데이터가 없습니다.")
    st.stop()


# =========================
# 사용 가능한 주택유형 목록
# =========================
available_internal_types = sorted(dong_df["property_type"].dropna().unique().tolist())
available_display_types = [reverse_property_type(x) for x in available_internal_types]

selected_display_type = st.selectbox(
    "주택유형을 선택해주세요",
    options=available_display_types
)

selected_internal_type = map_property_type(selected_display_type)

type_df = dong_df[dong_df["property_type"] == selected_internal_type].copy()

if type_df.empty:
    st.warning("선택한 주택유형 데이터가 없습니다.")
    st.stop()


# =========================
# 거래유형 선택
# =========================
available_rent_types = sorted(type_df["rent_type"].dropna().unique().tolist())

selected_rent_type = st.selectbox(
    "거래유형을 선택해주세요",
    options=available_rent_types
)

base_filtered = type_df[type_df["rent_type"] == selected_rent_type].copy()

if base_filtered.empty:
    st.warning("선택한 거래유형 데이터가 없습니다.")
    st.stop()


# =========================
# 실제 범위 계산
# =========================
deposit_min_real = int(base_filtered["deposit"].min())
deposit_max_real = int(base_filtered["deposit"].max())

st.info(f"보증금 실제 범위: {deposit_min_real:,}만원 ~ {deposit_max_real:,}만원")

deposit_range = st.slider(
    "보증금 범위를 선택해주세요 (만원)",
    min_value=deposit_min_real,
    max_value=deposit_max_real,
    value=(deposit_min_real, deposit_max_real)
)

monthly_range = None
if selected_rent_type == "월세":
    monthly_series = base_filtered["monthly_rent"].dropna()

    if monthly_series.empty:
        st.warning("월세 데이터가 없습니다.")
        st.stop()

    monthly_min_real = int(monthly_series.min())
    monthly_max_real = int(monthly_series.max())

    st.info(f"월세 실제 범위: {monthly_min_real:,}만원 ~ {monthly_max_real:,}만원")

    monthly_range = st.slider(
        "월세 범위를 선택해주세요 (만원)",
        min_value=monthly_min_real,
        max_value=monthly_max_real,
        value=(monthly_min_real, monthly_max_real)
    )


# =========================
# 검색 버튼
# =========================
search_clicked = st.button("검색", use_container_width=True)

if search_clicked:
    result_df = base_filtered.copy()

    result_df = result_df[
        (result_df["deposit"].fillna(-1) >= deposit_range[0]) &
        (result_df["deposit"].fillna(-1) <= deposit_range[1])
    ]

    if selected_rent_type == "월세" and monthly_range is not None:
        result_df = result_df[
            (result_df["monthly_rent"].fillna(-1) >= monthly_range[0]) &
            (result_df["monthly_rent"].fillna(-1) <= monthly_range[1])
        ]

    st.subheader("검색 조건")
    st.write(
        {
            "동": selected_dong,
            "주택유형": selected_display_type,
            "거래유형": selected_rent_type,
            "보증금 범위": f"{deposit_range[0]:,}만원 ~ {deposit_range[1]:,}만원",
            "월세 범위": f"{monthly_range[0]:,}만원 ~ {monthly_range[1]:,}만원" if monthly_range else "-"
        }
    )

    st.subheader(f"검색 결과: {len(result_df)}건")

    if result_df.empty:
        st.warning("조건에 맞는 결과가 없습니다.")
    else:
        display_df = make_display_table(result_df)
        st.dataframe(display_df, use_container_width=True, hide_index=True)