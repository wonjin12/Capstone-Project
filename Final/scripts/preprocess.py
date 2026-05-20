import pandas as pd
import os

output_dir = './output'

def preprocess_real_estate():
    # --- 1. 오피스텔 전처리 ---
    try:
        df_offi = pd.read_csv('data/officetel.csv', encoding='utf-8')
        # 주택유형 컬럼 추가 및 값 부여
        df_offi['주택유형'] = '오피스텔'
        cols_offi = ['시군구', '번지', '단지명', '전월세구분', '전용면적(㎡)', '보증금(만원)', '월세금(만원)', '도로명', '주택유형']
        df_offi = df_offi[cols_offi]
        df_offi.to_csv(os.path.join(output_dir, 'officetel.csv'), index=False, encoding='utf-8-sig')
        print("✅ 오피스텔 전처리 완료")
    except Exception as e:
        print(f"❌ 오피스텔 처리 중 오류: {e}")

    # --- 2. 아파트 전처리 ---
    try:
        df_apt = pd.read_csv('data/apt.csv', encoding='utf-8')
        cols_apt = ['시군구', '번지', '단지명', '전월세구분', '전용면적(㎡)', '보증금(만원)', '월세금(만원)', '도로명', '주택유형']
        df_apt = df_apt[cols_apt]
        df_apt.to_csv(os.path.join(output_dir, 'apt.csv'), index=False, encoding='utf-8-sig')
        print("✅ 아파트 전처리 완료")
    except Exception as e:
        print(f"❌ 아파트 처리 중 오류: {e}")

    # --- 3. 연립다세대(빌라) 전처리 ---
    try:
        df_villa = pd.read_csv('data/villa.csv', encoding='utf-8')
        cols_villa = ['시군구', '번지', '건물명', '전월세구분', '전용면적(㎡)', '보증금(만원)', '월세금(만원)', '도로명', '주택유형']
        df_villa = df_villa[cols_villa]
        df_villa.to_csv(os.path.join(output_dir, 'villa.csv'), index=False, encoding='utf-8-sig')
        print("✅ 빌라 전처리 완료")
    except Exception as e:
        print(f"❌ 빌라 처리 중 오류: {e}")

    # --- 4. 단독다가구 전처리 ---
    try:
        df_house = pd.read_csv('data/house.csv', encoding='utf-8')
        cols_house = ['시군구', '번지', '전월세구분', '계약면적(㎡)', '보증금(만원)', '월세금(만원)', '도로명', '주택유형']
        df_house = df_house[cols_house]
        df_house.to_csv(os.path.join(output_dir, 'house.csv'), index=False, encoding='utf-8-sig')
        print("✅ 단독다가구 전처리 완료")
    except Exception as e:
        print(f"❌ 단독다가구 처리 중 오류: {e}")

if __name__ == "__main__":
    preprocess_real_estate()