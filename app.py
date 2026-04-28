import chainlit as cl
import backend.kiwi_interface as kiwi_int
# 드디어 추가된 메인 로직 임포트!
import backend.main as main_logic 

@cl.on_chat_start
async def start():
    await cl.Message(
        content="✨ **서울시 구별 라이프스타일 분석 챗봇**에 오신 것을 환영합니다!"
    ).send()

    # '구' 입력 받기
    res = await cl.AskUserMessage(content="🏙️ 분석하고 싶은 **'구' 이름**을 입력해 주세요. (예: 마포구, 강남구)", timeout=60).send()
    if res:
        target_gu = res['output'].strip()
        cl.user_session.set("target_gu", target_gu)
        
        await cl.Message(content=f"📍 **'{target_gu}'** 지역을 기준으로 분석을 시작합니다.").send()

        # 요구사항 입력 받기
        req = await cl.AskUserMessage(
            content="💡 **원하시는 조건을 말씀해 주세요!**\n\n예: '지하철역이 가깝고 주변에 편의점이 많으면 좋겠어'", 
            timeout=120
        ).send()
        
        if req:
            await process_analysis(target_gu, req['output'])

async def process_analysis(target_gu, user_input):
    # 로딩 메시지
    msg = cl.Message(content=f"🔍 **'{user_input}'** 요청에 따라 {target_gu}의 데이터를 분석 중입니다...")
    await msg.send()

    # 1. 문장 분석 (Kiwi 사용)
    extracted_prefs = kiwi_int.analyze_user_sentence(user_input)
    
    # 2. 실제 분석 로직 실행 (main.py의 run_analysis 호출)
    # 가짜 데이터가 아니라 main.py에서 계산된 리스트를 가져옵니다.
    analysis_results = main_logic.run_analysis(target_gu, extracted_prefs)
    
    # 3. 결과 메시지 구성
    if not analysis_results:
        result_text = "❌ 분석 결과 적합한 장소를 찾지 못했습니다."
    else:
        result_text = f"### 📊 '{target_gu}' 지역 라이프스타일 분석 결과\n\n"
        for i, res in enumerate(analysis_results):
            medal = "🏆" if i == 0 else "🥈" if i == 1 else "🥉"
            result_text += f"{i+1}위: {medal} **{res['name']}** - `{res['total']}점` \n"
        
        result_text += "\n\n*설정한 조건(가중치)이 반영된 커스텀 점수입니다.*"
    
    # 최종 결과 전송
    await cl.Message(content=result_text).send()

@cl.on_message
async def main(message: cl.Message):
    # 추가 질문이나 재분석 요청 처리
    target_gu = cl.user_session.get("target_gu")
    await cl.Message(content=f"'{target_gu}' 분석 외에 다른 궁금한 점이 있으신가요?").send()