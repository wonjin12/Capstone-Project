Capstone Project
📌 프로젝트 개요

AI 기반 서울시 맞춤형 거주지 추천 및 실매물 탐색 시스템

📂 폴더 구조
frontend/ : UI 및 지도 (카카오맵)
backend/ : 추천 알고리즘 및 서버
data/ : 데이터 수집, 전처리, 좌표 매핑
docs/ : 기획서, 회의록, 발표자료

협업 방식 (Git 규칙)
🔴 main
최종 결과만 저장
직접 작업 ❌
🟡 dev
개발 통합 브랜치
feature 브랜치 결과 merge
🟢 feature 브랜치 (개인 작업)
각자 작업용 브랜치
예시:
feature/map
feature/data
feature/backend

작업 순서
# 1. 프로젝트 다운로드
git clone [저장소주소]

# 2. dev 브랜치 이동
git checkout dev

# 3. 개인 브랜치 생성
git checkout -b feature/이름

# 4. 작업 후 업로드
git add .
git commit -m "작업 내용"
git push origin feature/이름
