@echo off
echo ==========================================
echo 🏠 서울시 거주지 추천 시스템 실행 중…
echo ==========================================

:: 1. 챗봇 서버(Flask) 실행 (새 창에서 실행)
echo [1/2] Flask 서버를 시작합니다…
start cmd /k "python app_flask.py"

:: 2. 잠시 대기 (2초)
timeout /t 2 /nobreak > nul

:: 3. 매물 검색기(Streamlit) 실행
echo [2/2] Streamlit 매물 검색기를 시작합니다…
streamlit run app.py --server.headless true

pause