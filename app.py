from flask import Flask, request, jsonify, send_file
from pathlib import Path
from flask_cors import CORS
import os
from fields_loader import load_fields, load_questions
from engine import StudyCompassEngine
from ai_agent import CareerAIAgent

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
CORS(app)

# Load data + engine
fields = load_fields()
questions = load_questions()
engine = StudyCompassEngine(fields, questions)
ai_agent = CareerAIAgent()


@app.route("/", methods=["GET"])
def home():
    return send_file(BASE_DIR / "index.html")


@app.route('/api/next_question', methods=['GET'])
def get_next_question():
    q = engine.get_next_question()
    if q:
        return jsonify({"status": "question", "question": q})
    return jsonify({"status": "completed"})


@app.route('/api/answer', methods=['POST'])
def submit_answer():
    data = request.json or {}
    q_id = data.get('id')
    score = data.get('score')
    if q_id is None or score is None:
        return jsonify({"success": False, "error": "Missing id/score"}), 400
    engine.update_profile(q_id, float(score))
    return jsonify({"success": True})


@app.route('/api/reset', methods=['POST'])
def reset_engine():
    global engine
    engine = StudyCompassEngine(fields, questions)
    return jsonify({"status": "reset_success"})


@app.route('/api/final_report', methods=['POST'])
def generate_report():
    """
    Generates:
    - Top-3 recommendations (engine)
    - Final report (Groq) with a strict, grounded prompt
    """
    data = request.json or {}

    constraints = data.get("constraints", {}) or {}
    selected_values = data.get("selected_values", []) or []

    # Compute recommendations (engine)
    recs = engine.get_recommendations(constraints, selected_values)

    # Build structured dream data (DO NOT invent)
    dream_data = {
        "title": data.get("dream_title", "") or "",
        "dream_free_text": data.get("dream_reason", "") or "",  # optional free text
        "dream_value_choice": data.get("dream_value_choice", None),
        "dream_action_choice": data.get("dream_action_choice", None),
        "dream_barrier_choice": data.get("dream_barrier_choice", None),
    }

    # Context for the LLM final report
    ai_context = engine.get_full_context_for_ai(
        dream_data=dream_data,
        constraints=constraints,
        recommendations=recs
    )

    report = ai_agent.generate_report(ai_context)

    return jsonify({
        "recommendations": recs[:3],
        "report": report
    })


@app.route('/api/followup', methods=['POST'])
def followup():
    """
    ONE guided follow-up (not a free text question).
    """
    try:
        data = request.json or {}
        print(f"[FOLLOWUP] Received data: {data}")

        followup_type = (data.get("followup_type") or "").strip()
        selection = str(data.get("selection") or "").strip()

        if followup_type not in {"expand_recommendation", "expand_dream", "market_info"}:
            return jsonify({"success": False, "error": "Invalid followup_type"}), 400

        constraints = data.get("constraints", {}) or {}
        selected_values = data.get("selected_values", []) or []

        # Recompute engine recs
        print(f"[FOLLOWUP] Computing recommendations...")
        recs = engine.get_recommendations(constraints, selected_values)
        print(f"[FOLLOWUP] Got {len(recs)} recommendations")

        dream_title = (data.get("dream_title") or "").strip()
        print(f"[FOLLOWUP] Dream title: {dream_title}")

        # Get context
        print(f"[FOLLOWUP] Building context...")
        followup_context = engine.get_followup_context_for_ai(
            followup_type=followup_type,
            selection=selection,
            dream_title=dream_title,
            recommendations=recs
        )
        print(f"[FOLLOWUP] Context built: {len(followup_context)} chars")

        # Generate answer (NOTE: ai_agent.generate_followup only takes 1 param)
        print(f"[FOLLOWUP] Calling AI agent...")
        answer = ai_agent.generate_followup(followup_context)
        print(f"[FOLLOWUP] Answer generated: {len(answer)} chars")

        return jsonify({
            "success": True,
            "answer": answer
        })

    except Exception as e:
        print(f"[FOLLOWUP ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": f"שגיאה: {str(e)}"
        }), 500


@app.route('/api/values_list', methods=['GET'])
def get_values():
    values_map = {
        "innovation": "חדשנות ויצירתיות",
        "social_justice": "צדק חברתי",
        "security": "ביטחון ויציבות כלכלית",
        "intellectual_challenge": "אתגר אינטלקטואלי",
        "benevolence": "עזרה לזולת",
        "self_direction": "עצמאות וחופש פעולה",
        "power": "השפעה ומנהיגות",
        "integrity": "יושרה ואתיקה מקצועית"
    }
    return jsonify(values_map)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)



