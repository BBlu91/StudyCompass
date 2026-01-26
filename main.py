import time
import os
from fields_loader import load_fields, load_questions
from engine import StudyCompassEngine
from ai_agent import CareerAIAgent


# --- פונקציות עזר לשליטה בתצוגה ובקלט ---

def print_header(title):
    print("\n" + "=" * 55)
    print(f"      {title}      ")
    print("=" * 55 + "\n")


def get_validated_input(prompt, is_numeric=False, min_val=0.0, max_val=1.0):
    """מוודא שהמשתמש מכניס קלט תקין ולא ריק, תומך בבדיקה מספרית"""
    while True:
        user_input = input(prompt).strip()
        if not user_input:
            print("    >> השדה לא יכול להיות ריק. נא להזין תשובה.")
            continue

        if is_numeric:
            try:
                val = float(user_input)
                if min_val <= val <= max_val:
                    return val
                print(f"    >> נא להזין מספר בין {min_val} ל-{max_val}.")
            except ValueError:
                print("    >> קלט לא תקין. נא להזין מספר (למשל 0.7).")
        else:
            return user_input


def get_choice(question_text, options, guidance_text):
    """מציג אפשרויות עם משפט הדרכה לפני הרשימה"""
    print("-" * 35)
    print(f"--- {guidance_text} ---")
    for k, v in options.items():
        print(f"   {k}) {v}")

    while True:
        print(f"\n>>> {question_text}")
        c = input(f"בחירה (1-{len(options)}): ").strip()
        if c in options:
            return options[c]
        print(f"    >> בחירה לא תקינה. נא לבחור מספר בין 1 ל-{len(options)}.")


# --- שלבי השאלון ---

def run_interests_part(engine):
    print_header("PART 1: DISCOVERING YOUR INTERESTS")
    print("בשלב זה נלמד על הנטיות הטבעיות שלך ב-6 ממדים שונים.")
    print("ענה על סקאלה של 0.0 עד 1.0 (0=בכלל לא, 1=מאוד).\n")

    MAX_QUESTIONS = 18
    MIN_QUESTIONS = 10

    while len(engine.answered_ids) < MAX_QUESTIONS:
        question = engine.get_next_question()
        if not question: break

        count = len(engine.answered_ids) + 1
        val = get_validated_input(f"[{count}] {question['text_he']} (0-1): ", is_numeric=True)

        old_profile = engine.user_profile.copy()
        engine.update_profile(question['id'], val)

        if count >= MIN_QUESTIONS:
            diff = sum(abs(engine.user_profile[k] - old_profile[k]) for k in old_profile) / 6
            if diff < 0.015:
                print("\n[ המערכת זיהתה יציבות בפרופיל. עוברים לשלב הבא... ]")
                break


def run_magic_wand_part():
    print("\n" + "-" * 55)
    input("השלב הראשון הסתיים. לחץ ENTER כדי לעבור לשלב 'מטה הקסם'...")

    print_header("PART 2: THE MAGIC WAND (Dream Profile)")
    print("דמיין עולם שבו הלימודים בחינם וכל העבודות משלמות שכר זהה.")

    data = {}
    data['title'] = get_validated_input("\n1. מה היה המקצוע שלך בעולם החלומי הזה?\n   תשובה: ")

    data['value'] = get_choice(
        question_text="מהי הסיבה המרכזית שנמשכת למקצוע זה?",
        options={
            "1": "חופש ויצירתיות", "2": "עזרה לאחרים ושליחות",
            "3": "פתרון חידות ואתגר", "4": "סטטוס, השפעה ומנהיגות",
            "5": "סדר, יציבות ודיוק", "6": "תשוקה ועניין טבעי עמוק"
        },
        guidance_text="לפניך רשימת מניעים אפשריים, בחר את זה שמתאר אותך הכי טוב"
    )

    data['action'] = get_choice(
        question_text="מהי הפעולה שהיית רוצה לעשות רוב היום?",
        options={
            "1": "מחקר וגילוי עובדות", "2": "בנייה ותיקון דברים",
            "3": "ייעוץ והקשבה לאנשים", "4": "הובלה, שכנוע או הצגה",
            "5": "יצירה ועיצוב מקורי", "6": "למידה והעמקה בנושא מסוים"
        },
        guidance_text="להלן סוגי פעילויות, בחר את הפעילות המועדפת עליך"
    )

    data['barrier'] = get_choice(
        question_text="בעולם האמיתי, מה גורם לך להסס לגבי החלום הזה?",
        options={
            "1": "הלימודים נראים קשים או ארוכים מדי", "2": "חשש מיציבות כלכלית",
            "3": "חוסר ביטחון בכישרון שלי", "4": "לחץ מהסביבה או מהמשפחה",
            "5": "אין חסמים, רק מחפש את הדרך הנכונה"
        },
        guidance_text="לפניך חסמים נפוצים בבחירת קריירה, מה הכי רלוונטי אליך"
    )
    return data


def run_constraints_part():
    print_header("PART 3: REAL-WORLD CONSTRAINTS")
    print("כאן נבחן את האילוצים המציאותיים שלך (0=נמוך/קצר, 1=גבוה/ארוך).\n")
    constraints = {}
    keys = [('math_difficulty', 'נוחות עם רמה גבוהה של מתמטיקה'),
            ('training_length', 'נכונות ללימודים ארוכים (5+ שנים)'),
            ('study_intensity', 'יכולת עמידה בלחץ ועומס גבוה')]
    for k, label in keys:
        constraints[k] = get_validated_input(f"- {label} (0-1): ", is_numeric=True)
    return constraints


def run_values_part():
    print_header("PART 4: YOUR CORE VALUES")
    print("בחר את שלושת הערכים שהכי חשוב לך שיבואו לידי ביטוי בקריירה שלך:\n")

    v_list = {"1": ("innovation", "חדשנות ויצירתיות"), "2": ("benevolence", "חמלה ועזרה"),
              "3": ("integrity", "יושרה ואמת"), "4": ("power_influence", "השפעה ומנהיגות"),
              "5": ("self_direction", "עצמאות"), "6": ("universalism", "צדק חברתי"),
              "7": ("security", "ביטחון ויציבות"), "8": ("intellectual_challenge", "אתגר שכלי")}

    print("-" * 35)
    print("--- רשימת ערכי ליבה אפשריים ---")
    for k, v in v_list.items(): print(f"   {k}) {v[1]}")

    selected = []
    print("\n--- שלב הבחירה ---")
    while len(selected) < 3:
        remaining = 3 - len(selected)
        idx = input(f"   נותר לך לבחור {remaining} ערכים. הקלד מספר ערך: ").strip()
        if idx in v_list and v_list[idx][0] not in selected:
            selected.append(v_list[idx][0])
            print(f"      ✔ הוספת: {v_list[idx][1]}")
        else:
            print("    >> בחירה לא תקינה או ערך שנבחר כבר.")
    return selected, v_list


# --- MAIN EXECUTION ---

def main():
    try:
        # 1. טעינת נתונים ומנוע
        engine = StudyCompassEngine(load_fields(), load_questions())

        # 2. הרצת השאלון
        run_interests_part(engine)
        dream_data = run_magic_wand_part()
        constraints = run_constraints_part()
        selected_keys, v_map = run_values_part()

        # 3. חישוב והצגת המלצות ראשוניות מהמנוע
        print_header("RESULTS & RECOMMENDATIONS")
        print("מעבד נתונים סופי...\n")
        time.sleep(1.2)

        recs = engine.get_recommendations(constraints, selected_keys)

        for i, rec in enumerate(recs[:3]):
            print(f"{i + 1}. {rec['name']} ({rec['match_score']}%)")
            if rec['matched_values']:
                v_he = [v[1] for v in v_map.values() if v[0] in rec['matched_values']]
                print(f"   ערכים תואמים: {', '.join(v_he)}")
            print("-" * 35)

        # 4. הפקת הדו"ח האישי באמצעות הבינה המלאכותית
        ai_ctx = engine.get_full_context_for_ai(dream_data, constraints, recs)

        print("\n" + "*" * 55)
        print("         מחולל דו\"ח אישי מבוסס בינה מלאכותית")
        print("*" * 55)
        print("המערכת מנתחת כעת את הקשר בין השאיפות שלך להמלצות... זה ייקח רגע.")

        try:
            agent = CareerAIAgent()
            report = agent.generate_report(ai_ctx)

            print("\n" + "=" * 55)
            print("              הדו\"ח האישי המלא שלך")
            print("=" * 55)
            print(report)
            print("\n" + "=" * 55)
        except Exception as ai_err:
            print(f"AI Report Generation Failed: {ai_err}")

        return ai_ctx

    except Exception as e:
        print(f"\nCritical System Error: {e}")


if __name__ == "__main__":
    main()