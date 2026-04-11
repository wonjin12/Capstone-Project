import pandas as pd
import json
from pathlib import Path

# =========================
# 경로 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "../data"
HTML_DIR = BASE_DIR / "../html"

SUBWAY_PATH = DATA_DIR / "subway_data.csv"
SHOP_PATH = DATA_DIR / "seoul_shop_data.csv"
GU_GEO_PATH = HTML_DIR / "seoul_gu_geo.json"

SUBWAY_JSON_PATH = HTML_DIR / "subway_points.json"
SHOP_JSON_PATH = HTML_DIR / "shop_points.json"

# =========================
# Point in Polygon 함수
# =========================
def point_in_polygon(x, y, polygon):
    """
    x = 경도(lng), y = 위도(lat)
    polygon = [[lng, lat], [lng, lat], ...]
    """
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]

    for i in range(n + 1):
        p2x, p2y = polygon[i % n]

        if min(p1y, p2y) < y <= max(p1y, p2y):
            if x <= max(p1x, p2x):
                if p1y != p2y:
                    xinters = (y - p1y) * (p2x - p1x) / ((p2y - p1y) + 1e-12) + p1x
                else:
                    xinters = p1x

                if p1x == p2x or x <= xinters:
                    inside = not inside

        p1x, p1y = p2x, p2y

    return inside

# =========================
# GeoJSON 로드
# =========================
with open(GU_GEO_PATH, "r", encoding="utf-8") as f:
    gu_geo = json.load(f)

gu_polygons = []

for feature in gu_geo["features"]:
    gu_name = feature["properties"].get("name", "")
    geometry = feature["geometry"]

    if geometry["type"] == "Polygon":
        outer = geometry["coordinates"][0]
        gu_polygons.append({
            "gu": gu_name,
            "polygon": outer
        })

    elif geometry["type"] == "MultiPolygon":
        for polygon_coords in geometry["coordinates"]:
            outer = polygon_coords[0]
            gu_polygons.append({
                "gu": gu_name,
                "polygon": outer
            })

def find_gu_by_point(lng, lat):
    for item in gu_polygons:
        if point_in_polygon(lng, lat, item["polygon"]):
            return item["gu"]
    return ""

# =========================
# 1. 지하철 데이터 로드
# =========================
try:
    subway = pd.read_csv(SUBWAY_PATH, encoding="utf-8")
except Exception:
    subway = pd.read_csv(SUBWAY_PATH, encoding="cp949")

# 유정님 실제 지하철 컬럼 기준
subway = subway.rename(columns={
    "역한글명칭": "name",
    "환승역Y좌표": "lat",
    "환승역X좌표": "lng",
    "호선명칭": "line"
})

required_subway_cols = ["name", "lat", "lng"]
for col in required_subway_cols:
    if col not in subway.columns:
        raise ValueError(f"지하철 데이터에 '{col}' 컬럼이 없습니다. 실제 컬럼명을 다시 확인해주세요.")

# line 컬럼이 없을 경우 대비
if "line" not in subway.columns:
    subway["line"] = ""

subway = subway[["name", "lat", "lng", "line"]].dropna(subset=["name", "lat", "lng"])

subway["lat"] = pd.to_numeric(subway["lat"], errors="coerce")
subway["lng"] = pd.to_numeric(subway["lng"], errors="coerce")
subway = subway.dropna(subset=["lat", "lng"])

# 지하철역이 어느 구에 속하는지 계산
subway["gu"] = subway.apply(lambda row: find_gu_by_point(row["lng"], row["lat"]), axis=1)

subway_points = subway.to_dict(orient="records")

# =========================
# 2. 상권 데이터 로드
# =========================
cols = ["상호명", "상권업종소분류명", "시군구명", "행정동명", "경도", "위도"]

try:
    shop = pd.read_csv(
        SHOP_PATH,
        header=1,
        usecols=cols,
        encoding="cp949"
    )
except UnicodeDecodeError:
    shop = pd.read_csv(
        SHOP_PATH,
        header=1,
        usecols=cols,
        encoding="utf-8-sig"
    )

# 필요한 업종만 우선 필터링
target_categories = ["카페", "커피", "편의점", "병원"]

shop = shop[
    shop["상권업종소분류명"].astype(str).str.contains("|".join(target_categories), na=False)
].copy()

shop = shop.rename(columns={
    "상호명": "name",
    "상권업종소분류명": "category",
    "시군구명": "gu",
    "행정동명": "dong",
    "위도": "lat",
    "경도": "lng"
})

shop = shop[["name", "category", "gu", "dong", "lat", "lng"]].dropna(subset=["name", "lat", "lng", "gu"])

shop["lat"] = pd.to_numeric(shop["lat"], errors="coerce")
shop["lng"] = pd.to_numeric(shop["lng"], errors="coerce")
shop = shop.dropna(subset=["lat", "lng"])

shop_points = shop.to_dict(orient="records")

# =========================
# 3. JSON 저장
# =========================
with open(SUBWAY_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(subway_points, f, ensure_ascii=False, indent=2)

with open(SHOP_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(shop_points, f, ensure_ascii=False, indent=2)

print("✅ JSON 저장 완료")
print(f"지하철 포인트 수: {len(subway_points)}")
print(f"상권 포인트 수: {len(shop_points)}")

print("\n[지하철 샘플]")
print(subway.head())

print("\n[상권 샘플]")
print(shop.head())