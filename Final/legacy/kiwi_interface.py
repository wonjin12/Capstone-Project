# kiwi_interface.py
from kiwipiepy import Kiwi
try:
    import legacy.main as main
except ModuleNotFoundError:
    import legacy.main as main

kiwi = Kiwi()

def analyze_user_sentence(sentence):
    # (기존 prefs 및 mapping 로직은 동일)
    prefs = {
        '지하철_근접_user': 1.0, '지하철_밀도_user': 1.0,
        '카페_근접_user': 1.0, '카페_밀도_user': 1.0,
        '병원_근접_user': 1.0, '병원_밀도_user': 1.0,
        '편의점_근접_user': 1.0, '편의점_밀도_user': 1.0
    }
    
    tokens = kiwi.tokenize(sentence)
    words = [t.form for t in tokens]
    
    mapping = {
        '지하철': (['지하철', '역'], '지하철'),
        '카페': (['카페', '커피'], '카페'),
        '병원': (['병원', '의료'], '병원'),
        '편의점': (['편의점', '마트'], '편의점')
    }

    proximity_words = ['가깝', '근처', '앞', '출구', '단지', '옆', '급할', '응급', '슬세권', '바로']
    density_words = ['많', '여러', '환승', '교통', '거리', '상권', '핫플', '다양', '인프라', '사방', '천지']

    for item, (trigger_words, key_prefix) in mapping.items():
        if any(w in words for w in trigger_words):
            if any(w in words for w in proximity_words):
                prefs[f'{key_prefix}_근접_user'] = 5.0
            if any(w in words for w in density_words):
                prefs[f'{key_prefix}_밀도_user'] = 5.0

    return prefs

def start_smart_chatbot():
    # 터미널용 실행 코드도 '구'로 변경
    target_gu = input("분석하고 싶은 '구' 이름을 입력하세요 (예: 마포구): ").strip()
    user_input = input("당신의 요구사항을 입력하세요: ")
    extracted_prefs = analyze_user_sentence(user_input)
    main.run_analysis(target_gu, extracted_prefs)