from pathlib import Path
import pandas as pd
import streamlit as st
import re  # [추가] 정규표현식 모듈

# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="서울시 거주지 추천 & 매물 검색",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 서울시 실거래가 통합 검색")

# =========================
# 파일 경로 및 데이터 로드
# =========================
current_dir = Path(__file__).parent
transaction_path = current_dir / "data" / "transaction_unified.csv"

@st.cache_data
def load_transaction_data(file_path: Path) -> pd.DataFrame:
    if not file_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(file_path, encoding="utf-8-sig")
    
    # 숫자형 변환 및 문자열 정제
    for col in ["deposit", "monthly_rent", "area_m2", "floor"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["gu", "dong", "property_type", "rent_type", "address", "complex_name"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    return df

df_raw = load_transaction_data(transaction_path)

# =========================
# URL 파라미터 읽기 및 보정
# =========================
query_params = st.query_params
url_dong = query_params.get("dong")

# 헬퍼 함수: 주택 유형 매핑
def reverse_property_type(val):
    mapping = {"아파트": "아파트", "단독다가구": "주택", "연립다세대": "빌라", "오피스텔": "오피스텔"}
    return mapping.get(val, val)

def map_property_type(val):
    mapping = {"아파트": "아파트", "주택": "단독다가구", "빌라": "연립다세대", "오피스텔": "오피스텔"}
    return mapping.get(val, val)

# =========================
# 사이드바 검색 필터 (자동 세팅 로직)
# =========================
st.sidebar.header("🔍 검색 필터")

# 1. 초기 기본값 설정
all_gu = sorted(df_raw["gu"].unique())
default_gu_idx = all_gu.index("광진구") if "광진구" in all_gu else 0
default_dong_idx = 0

# 2. URL 파라미터가 있을 경우 위치 찾기 (이름 보정 로직 적용)
if url_dong:
    # [핵심] '남가좌2동' -> '남가좌' 추출 (숫자와 끝의 '동' 제거)
    clean_keyword = re.sub(r'[0-9]|동$', '', url_dong)
    
    # 데이터셋의 동 이름 중 해당 키워드가 포함된 행 찾기
    target_rows = df_raw[df_raw["dong"].str.contains(clean_keyword)]
    
    if not target_rows.empty:
        found_gu = target_rows.iloc[0]["gu"]
        found_dong = target_rows.iloc[0]["dong"] # 실제 데이터상의 이름 (예: 남가좌동)
        
        # 구 인덱스 업데이트
        if found_gu in all_gu:
            default_gu_idx = all_gu.index(found_gu)
            
        # 해당 구의 동 리스트에서 인덱스 찾기
        temp_all_dong = sorted(df_raw[df_raw["gu"] == found_gu]["dong"].unique())
        if found_dong in temp_all_dong:
            default_dong_idx = temp_all_dong.index(found_dong)
        
        st.success(f"✅ 챗봇 추천 지역인 **{found_gu} {found_dong}** 매물을 먼저 보여드립니다.")
    else:
        st.warning(f"ℹ️ 추천받은 '{url_dong}'에 대한 매물 데이터를 찾을 수 없어 기본 지역을 표시합니다.")

# 사이드바 위젯 생성
selected_gu = st.sidebar.selectbox("구 선택", all_gu, index=default_gu_idx)

all_dong = sorted(df_raw[df_raw["gu"] == selected_gu]["dong"].unique())

# 구를 수동으로 바꿨을 때도 URL의 동네가 해당 구에 있다면 인덱스 유지
if url_dong:
    clean_keyword = re.sub(r'[0-9]|동$', '', url_dong)
    current_url_rows = df_raw[(df_raw["gu"] == selected_gu) & (df_raw["dong"].str.contains(clean_keyword))]
    if not current_url_rows.empty:
        current_url_dong = current_url_rows.iloc[0]["dong"]
        if current_url_dong in all_dong:
            default_dong_idx = all_dong.index(current_url_dong)

selected_dong = st.sidebar.selectbox("동 선택", all_dong, index=default_dong_idx)

# 나머지 필터들
selected_display_type = st.sidebar.selectbox("주택 유형", ["전체", "아파트", "주택", "빌라", "오피스텔"])
selected_rent_type = st.sidebar.selectbox("거래 유형", ["전체", "전세", "월세"])
max_dep = int(df_raw["deposit"].max()) if not df_raw["deposit"].empty else 100000
deposit_range = st.sidebar.slider("보증금 범위 (만원)", 0, max_dep, (0, max_dep))

# =========================
# 데이터 필터링 및 출력
# =========================
filtered_df = df_raw.copy()
filtered_df = filtered_df[filtered_df["gu"] == selected_gu]

if selected_display_type != "전체":
    filtered_df = filtered_df[filtered_df["property_type"] == map_property_type(selected_display_type)]
if selected_rent_type != "전체":
    filtered_df = filtered_df[filtered_df["rent_type"] == selected_rent_type]

filtered_df = filtered_df[(filtered_df["deposit"] >= deposit_range[0]) & (filtered_df["deposit"] <= deposit_range[1])]

# 챗봇이 추천/선택한 동네에 우선순위 부여
filtered_df["priority"] = filtered_df["dong"].apply(lambda x: 1 if x == selected_dong else 0)
result_df = filtered_df.sort_values(by=["priority", "deposit"], ascending=[False, True])

st.subheader(f"✨ {selected_dong} 추천 및 {selected_gu} 검색 결과")

if result_df.empty:
    st.warning("조건에 맞는 매물이 없습니다.")
else:
    display_df = pd.DataFrame()
    display_df["구분"] = result_df["priority"].apply(lambda x: "⭐ 추천" if x == 1 else "일반")
    display_df["동네"] = result_df["dong"]
    display_df["단지명"] = result_df["complex_name"]
    display_df["유형"] = result_df["property_type"].apply(reverse_property_type)
    display_df["거래"] = result_df["rent_type"]
    display_df["보증금"] = result_df["deposit"].apply(lambda x: f"{int(x):,}만원")
    display_df["월세"] = result_df["monthly_rent"].apply(lambda x: f"{int(x):,}만원" if x > 0 else "-")
    display_df["면적"] = result_df["area_m2"].apply(lambda x: f"{x:.1f}㎡")
    display_df["층"] = result_df["floor"].apply(lambda x: f"{int(x)}층" if x > 0 else "-")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()
st.caption("※ 본 데이터는 국토교통부 실거래가 데이터를 기반으로 제공됩니다.")