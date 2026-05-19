from pathlib import Path
import pandas as pd
import streamlit as st
import re

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
transaction_json_path = current_dir / "data" / "transaction_unified.json"

@st.cache_data
def load_transaction_json(file_path: Path) -> pd.DataFrame:
    if not file_path.exists():
        return pd.DataFrame()
    
    df = pd.read_json(file_path)
    
    string_cols = ["gu", "dong", "property_type", "rent_type", "address", "complex_name"]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            
    numeric_cols = ["deposit", "monthly_rent", "area_m2", "floor"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
    return df

df_raw = load_transaction_json(transaction_json_path)

def get_pure_name(name_str):
    """
    지명 핵심어만 추출하는 전처리 함수
    """
    if not name_str:
        return ""
    name = name_str.replace(" ", "")
    name = re.sub(r'(동|가)$', '', name)
    name = re.sub(r'[0-9]$', '', name)
    name = re.sub(r'(동|가)$', '', name)
    name = re.sub(r'[0-9]$', '', name)
    return name

# =============================================================
# 행정동-법정동 매핑 데이터셋 (수궁동 및 구로구 통합 반영)
# =============================================================
ADMIN_TO_LEGAL_DONG = {
    "서강동": ["창전동", "상수동", "하중동", "신정동", "당인동"],
    "종로1.2.3.4가동": ["종로1가", "종로2가", "종로3가", "종로4가", "인사동", "낙원동", "피맛골", "청진동", "서린동", "수송동", "훈정동", "묘동", "봉익동", "돈의동", "장사동", "관수동", "관철동"],
    "종로5.6가동": ["종로5가", "종로6가", "연지동", "효제동"],
    "신촌동": ["대현동", "대신동", "신촌동", "봉원동", "창천동"],  
    "충현동": ["충정로2가", "충정로3가", "합동", "미근동", "북아현동"],  
    "회현동": ["회현동1가", "회현동2가", "회현동3가", "남창동", "봉래동1가", "순화동"],
    "명동": ["명동1가", "명동2가", "충무로1가", "충무로2가", "저동1가", "삼각동", "수하동", "장교동", "수표동", "인현동1가", "예장동", "회현동2가"],
    "을지로동": ["을지로3가", "을지로4가", "을지로5가", "주교동", "방산동", "입정동", "산림동", "초동"],
    "소공동": ["소공동", "북창동", "태평로2가", "서소문동", "정동", "순화동", "의주로1가", "충정로1가"],
    "광희동": ["광희동1가", "광희동2가", "쌍림동", "을지로6가", "을지로7가", "오장동", "충무로4가", "충무로5가"],
    "필동": ["필동1가", "필동2가", "필동3가", "주자동", "예장동", "충무로3가"],
    "장충동": ["장충동1가", "장충동2가", "묵정동"],
    "수궁동": ["궁동", "온수동"],  # 👈 구로구 수궁동 매핑 추가 완료!
    "신도림동": ["신도림동"],  # 구로구 연계 추가
    "구로동": ["구로동"],  # 구로구 연계 추가
    "한강로동": ["한강로1가", "한강로2가", "한강로3가", "용산동3가", "용산동5가", "문배동", "신계동"],
    "혜화동": ["혜화동", "명륜1가", "명륜2가", "명륜3가", "명륜4가"]
}

# 역방향 매핑 사전 구축
LEGAL_TO_ADMIN_DONG = {}
for admin_d, legal_list in ADMIN_TO_LEGAL_DONG.items():
    for l_d in legal_list:
        LEGAL_TO_ADMIN_DONG[l_d] = admin_d

# =========================
# URL 파라미터 처리 및 세션 주입
# =========================
query_params = st.query_params
url_query = query_params.get("query")

all_gu = sorted(df_raw["gu"].unique()) if not df_raw.empty else []

if url_query and st.session_state.get("processed_query") != url_query:
    st.session_state["processed_query"] = url_query
    
    matched_gu = None
    matched_dong = None
    
    query_words = re.findall(r'[가-힣0-9\·\.]+', url_query)
    
    # 1. 행정동 사전 직접 매칭 검사
    found_admin_dong = None
    for admin_dong in ADMIN_TO_LEGAL_DONG.keys():
        if admin_dong in url_query or get_pure_name(admin_dong) in [get_pure_name(w) for w in query_words]:
            found_admin_dong = admin_dong
            break
            
    if found_admin_dong:
        matched_dong = found_admin_dong
        legal_candidates = ADMIN_TO_LEGAL_DONG[found_admin_dong]
        db_match_rows = df_raw[df_raw["dong"].isin(legal_candidates)]
        if not db_match_rows.empty:
            matched_gu = db_match_rows.iloc[0]["gu"]

    # 2. 행정동 이름으로 걸리지 않은 경우
    if not matched_dong:
        for _, row in df_raw[["gu", "dong"]].drop_duplicates().iterrows():
            d_name = row["dong"]
            if d_name in query_words:
                matched_dong = d_name
                matched_gu = row["gu"]
                break
                
            pure_db_dong = get_pure_name(d_name)
            is_pured_match = False
            for w in query_words:
                if w in all_gu or w == "서울시":
                    continue
                pure_url_word = get_pure_name(w)
                if pure_db_dong and pure_url_word and (pure_db_dong == pure_url_word):
                    is_pured_match = True
                    break
                    
            if is_pured_match:
                matched_dong = d_name
                matched_gu = row["gu"]
                break

    if matched_gu:
        st.session_state["target_gu"] = matched_gu
    if matched_dong:
        st.session_state["target_dong"] = matched_dong
    else:
        if "target_dong" in st.session_state:
            del st.session_state["target_dong"]

# 헬퍼 함수
def reverse_property_type(val):
    mapping = {"아파트": "아파트", "단독다가구": "주택", "연립다세대": "빌라", "오피스텔": "오피스텔"}
    return mapping.get(val, val)

def map_property_type(val):
    mapping = {"아파트": "아파트", "주택": "단독다가구", "빌라": "연립다세대", "오피스텔": "오피스텔"}
    return mapping.get(val, val)

# =========================
# 사이드바 검색 필터
# =========================
st.sidebar.header("🔍 검색 필터")

if df_raw.empty:
    st.error("데이터를 불러오지 못했습니다. 경로와 파일명을 확인해 주세요.")
    st.stop()

# 1. 구 선택 위젯
default_gu_name = st.session_state.get("target_gu", "광진구")
if default_gu_name not in all_gu:
    default_gu_name = all_gu[0]
default_gu_idx = all_gu.index(default_gu_name)

selected_gu = st.sidebar.selectbox("구 선택", all_gu, index=default_gu_idx)

if "target_gu" in st.session_state and selected_gu != st.session_state["target_gu"]:
    if "target_dong" in st.session_state:
        del st.session_state["target_dong"]

# 2. 동 선택 위젯 구성
all_dong = sorted(df_raw[df_raw["gu"] == selected_gu]["dong"].unique())

for admin_dong, legal_list in ADMIN_TO_LEGAL_DONG.items():
    if any(l_dong in all_dong for l_dong in legal_list):
        if admin_dong not in all_dong:
            all_dong.append(admin_dong)

all_dong = sorted(all_dong) 

# 기본값 인덱스 설정
default_dong_idx = 0
target_session_dong = st.session_state.get("target_dong", "")

if target_session_dong in all_dong:
    default_dong_idx = all_dong.index(target_session_dong)
elif target_session_dong in LEGAL_TO_ADMIN_DONG:
    admin_home = LEGAL_TO_ADMIN_DONG[target_session_dong]
    if admin_home in all_dong:
        default_dong_idx = all_dong.index(admin_home)

selected_dong = st.sidebar.selectbox("동 선택", all_dong, index=default_dong_idx)

# 3. 알림 제어
if target_session_dong and (selected_dong == target_session_dong or selected_dong in ADMIN_TO_LEGAL_DONG.get(target_session_dong, [])):
    st.success(f"✅ 추천 권역인 **{selected_gu} {target_session_dong}** 관할 매물 통합 검색 모드입니다.")

selected_display_type = st.sidebar.selectbox("주택 유형", ["전체", "아파트", "주택", "빌라", "오피스텔"])
selected_rent_type = st.sidebar.selectbox("거래 유형", ["전체", "전세", "월세"])
max_dep = int(df_raw["deposit"].max()) if not df_raw["deposit"].empty else 100000
deposit_range = st.sidebar.slider("보증금 범위 (만원)", 0, max_dep, (0, max_dep))

# =================================================================
# 데이터 필터링 및 출력
# =================================================================
filtered_df = df_raw.copy()
filtered_df = filtered_df[filtered_df["gu"] == selected_gu]

if selected_display_type != "전체":
    filtered_df = filtered_df[filtered_df["property_type"] == map_property_type(selected_display_type)]
if selected_rent_type != "전체":
    filtered_df = filtered_df[filtered_df["rent_type"] == selected_rent_type]

filtered_df = filtered_df[(filtered_df["deposit"] >= deposit_range[0]) & (filtered_df["deposit"] <= deposit_range[1])]

target_dongs_list = [selected_dong]

if selected_dong in ADMIN_TO_LEGAL_DONG:
    target_dongs_list = ADMIN_TO_LEGAL_DONG[selected_dong]
elif selected_dong in LEGAL_TO_ADMIN_DONG:
    admin_home = LEGAL_TO_ADMIN_DONG[selected_dong]
    target_dongs_list = ADMIN_TO_LEGAL_DONG[admin_home]

filtered_df = filtered_df[filtered_df["dong"].isin(target_dongs_list)]

def check_priority(db_dong):
    if db_dong == selected_dong:
        return 2
    return 1

filtered_df["priority"] = filtered_df["dong"].apply(check_priority)
result_df = filtered_df.sort_values(by=["priority", "deposit"], ascending=[False, True])

st.subheader(f"✨ {selected_dong} 관할 권역 통합 검색 결과 (총 {len(result_df)}건)")

if result_df.empty:
    st.warning("조건에 맞는 매물이 없습니다.")
else:
    display_df = pd.DataFrame()
    
    display_df["구분"] = result_df["dong"].apply(
        lambda x: "⭐ 해당동" if x == selected_dong else "🔍 관할법정동"
    )
    display_df["동네"] = result_df["dong"]
    display_df["단지명"] = result_df["complex_name"]
    display_df["유형"] = result_df["property_type"].apply(reverse_property_type)
    display_df["거래"] = result_df["rent_type"]
    display_df["보증금"] = result_df["deposit"].apply(lambda x: f"{int(x):,}만원")
    display_df["월세"] = result_df["monthly_rent"].apply(lambda x: f"{int(x):,}만원" if x > 0 else "-")
    display_df["면적"] = result_df["area_m2"].apply(lambda x: f"{x:.1f}㎡")
    
    if "floor" in result_df.columns:
        display_df["층"] = result_df["floor"].apply(lambda x: f"{int(x)}층" if x > 0 else "-")
    else:
        display_df["층"] = "-"

    st.dataframe(display_df, width='stretch', hide_index=True)

st.divider()
st.caption("※ 본 데이터는 국토교통부 실거래가 데이터를 기반으로 제공됩니다.")