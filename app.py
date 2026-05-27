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
# 💡 .resolve()를 사용하여 실행 위치와 상관없이 실제 app.py 파일 위치 기준으로 data 폴더를 탐색합니다.
current_dir = Path(__file__).resolve().parent
transaction_json_path = current_dir / "data" / "transaction_unified.json"

from backend.legal_dong import ADMIN_TO_LEGAL_DONG

@st.cache_data
def load_transaction_json(file_path: Path) -> pd.DataFrame:
    # 🚨 파일이 지정된 위치에 없을 경우 에러와 함께 실제 탐색 경로를 화면에 출력합니다.
    if not file_path.exists():
        st.error("❌ [파일 탐색 실패] 실거래가 데이터 파일을 찾지 못했습니다!")
        st.warning("코드가 데이터를 찾으려고 확인한 맥북 내부 주소는 다음과 같습니다:")
        st.code(str(file_path.resolve()))
        st.info("💡 위 주소에 실제로 'data' 폴더와 'transaction_unified.json' 파일이 들어있는지 확인해주세요.")
        return pd.DataFrame()
    
    try:
        df = pd.read_json(file_path)
    except Exception as e:
        st.error(f"❌ [파일 파싱 실패] 파일은 찾았으나 내부 데이터 구조가 깨졌습니다: {e}")
        return pd.DataFrame()
    
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
        else:
            # 💡 사전에는 있으나 실제 데이터베이스(df_raw)에 매물이 아예 없는 경우 (예: 보라매동, 서원동 등)
            # 엉뚱한 타 권역으로 튕기지 않도록 URL 텍스트 분석 및 키워드로 구를 매칭합니다.
            for gu_candidate in all_gu:
                if gu_candidate in url_query:
                    matched_gu = gu_candidate
                    break
            
            if not matched_gu:
                if any(k in url_query for k in ["보라매", "서원", "은천", "신림", "남현", "봉천", "관악"]):
                    matched_gu = "관악구"
                elif any(k in url_query for k in ["면목", "중랑", "망우"]):
                    matched_gu = "중랑구"

    # 2. 행정동 이름으로 걸리지 않은 경우 (법정동 기준 매칭)
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

    # 💡 [보완된 방어선] 행정동/법정동 모두 매칭되지 않은 예외 텍스트일 때만 글자를 유지하도록 제한합니다.
    # 면목본동이나 보라매동이 여기서 무차별적으로 덮어씌워지는 현상을 방지합니다.
    if not matched_dong:
        for w in query_words:
            if "동" in w and len(w) >= 3:
                if w not in ADMIN_TO_LEGAL_DONG:
                    matched_dong = w
                    break

    # 최종 구 이름 백업 보완 로직
    if matched_dong and not matched_gu:
        if "면목" in matched_dong: matched_gu = "중랑구"
        elif "신림" in matched_dong or "보라매" in matched_dong or "서원" in matched_dong or "은천" in matched_dong: matched_gu = "관악구"

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
default_gu_name = st.session_state.get("target_gu", "관악구")
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

# 데이터에 없는 행정동(보라매동 등) 링크로 유입된 경우 셀렉트박스 튕김 방지를 위해 강제 포함
target_session_dong = st.session_state.get("target_dong", "")
if target_session_dong and target_session_dong not in all_dong:
    all_dong.append(target_session_dong)

all_dong = sorted(all_dong) 

# 기본값 인덱스 설정
default_dong_idx = 0

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

if not filtered_df.empty:
    filtered_df["priority"] = filtered_df["dong"].apply(check_priority)
    result_df = filtered_df.sort_values(by=["priority", "deposit"], ascending=[False, True])
else:
    result_df = pd.DataFrame()

st.subheader(f"✨ {selected_dong} 관할 권역 통합 검색 결과 (총 {len(result_df)}건)")

# 💡 데이터가 없으면 확실하게 해당 구/동 경고창을 띄우고 종료합니다.
if result_df.empty:
    st.warning(f"⚠️ 현재 {selected_gu} {selected_dong}에 조건에 맞는 실거래가 매물이 없습니다.")
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