import pandas as pd

df = pd.read_csv("seoul_shop_data.csv",
    encoding="utf-8"
)

df.loc[
    (df["상권업종대분류명"] == "음식") &
    (df["상권업종소분류명"] != "카페"),
    "상권업종소분류명"
] = "음식점"

df.to_csv("seoul_shop_data_clean.csv", index=False, encoding="utf-8-sig")