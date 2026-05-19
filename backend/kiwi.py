from kiwipiepy import Kiwi
try:
    import backend.main as main
except ModuleNotFoundError:
    import main

kiwi = Kiwi()

def analyze_user_sentence(sentence):

    mapping = {
        '카페': (['카페', '커피'], '카페'),
        '음식점' : (['맛집', '음식점'], '음식점'),
        '편의점': (['편의점','gs25'], '편의점'),
        '마트': (['홈플러스', '마트'], '마트'),
        '약국': (['약국'], '약국'),
        '병원': (['병원', '응급실'], '병원'),
        '여가시설': (['술', '담배'], '여가시설'),
        '운동시설': (['운동장', '운동시설'], '운동시설'),
        '학원': (['학원', '공부'], '학원'),
        '미용실': (['미용실', '머리'], '미용실'),
        '세탁소': (['세탁소','빨래'], '세탁소'),
        '지하철역': (['지하철', '역'], '지하철역')
    }

    prefs = {}
    for key in mapping.keys():
        prefs[f'{key}_근접_user'] = 1.0
        prefs[f'{key}_밀도_user'] = 1.0
    
    tokens = kiwi.tokenize(sentence)
    words = [t.form for t in tokens]

    proximity_words = ['가깝', '근처', '앞', '출구', '단지', '옆', '급할', '응급', '슬세권', '바로']
    density_words = ['많', '여러', '환승', '교통', '거리', '상권', '핫플', '다양', '인프라', '사방', '천지']

    for item, (trigger_words, key_prefix) in mapping.items():
        if any(trigger in w for w in words for trigger in trigger_words):
            if any(w in words for w in proximity_words):
                prefs[f'{key_prefix}_근접_user'] = 5.0
            if any(w in words for w in density_words):
                prefs[f'{key_prefix}_밀도_user'] = 5.0

    return prefs