from flask import Flask, request, jsonify
from flask_cors import CORS
import backend.kiwi_interface as kiwi_int
import backend.main as main_logic

app = Flask(__name__)
CORS(app)  # HTML과 통신 허용

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_input = data.get('message')
        target_gu = data.get('gu')

        extracted_prefs = kiwi_int.analyze_user_sentence(user_input)
        
        analysis_results = main_logic.run_analysis(target_gu, extracted_prefs)

        return jsonify({
            "status": "success",
            "results": analysis_results # [{name: '동이름', total: 점수}, ...]
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Flask 서버는 5000번 포트에서 대기합니다.
    app.run(host='127.0.0.1', port=5000, debug=True)