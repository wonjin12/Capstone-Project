#!/bin/bash
# 1. 챗봇 서버(Flask) 실행
python3 app_flask.py & 

# 2. 잠시 대기 (Flask가 켜질 시간을 줍니다)
sleep 2

# 3. 매물 검색기(Streamlit) 실행
python3 -m streamlit run app.py
