import os
from groq import Groq
from dotenv import load_dotenv

# Load .env for local development (Render provides env vars directly)
load_dotenv()


class CareerAIAgent:
    """Thin wrapper around Groq chat completions with safe, grounded prompts."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = "llama-3.3-70b-versatile"
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def _ensure_client(self):
        if not self.client:
            return False, "GROQ_API_KEY is missing on the server."
        return True, None

    # ---------------------------
    # Final report
    # ---------------------------
    def generate_report(self, ai_context: str) -> str:
        """Generate the final report shown to the user."""

        ok, err = self._ensure_client()
        if not ok:
            return err

        system_prompt = """
 אתה StudyCompass Report Generator.

מטרה:
להפיק דו״ח מסכם, שקוף, מקצועי ולא-פסיכולוגי לבחירת תחום לימודים.

עקרונות מחייבים:
1) אין להמציא חסמים, קשיים, פחדים, מגבלות או אבחנות.
2) אין לבצע ניתוח פסיכולוגי/טיפולי.
3) כל טענה חייבת להישען במפורש על נתון שהתקבל בקלט.
4) חסמים מותר לציין רק אם קיימים בנתון dream_barrier_choice.
5) אל תתמקד בשכר / כסף בדו״ח הראשי. אם מופיע נתון שוק עבודה בקלט, התעלם ממנו בדו״ח הראשי.

הבהרה חשובה (כדי למנוע תשובות שטחיות):
- מותר ואף רצוי להסביר *מדוע* נתון מסוים מוביל להמלצה מסוימת.
- מותר לקשר בין נטיות, סוג עשייה ותחומי לימוד באופן ענייני ומנומק.
- אם חסר מידע מסוים, יש לציין זאת במפורש ולא לנחש.

פירוש שדות (קריטי):
- math_difficulty מייצג נוחות עם מתמטיקה: 1=נוחות גבוהה, 0=נוחות נמוכה.
  אסור להציג זאת כקושי/חסם.
- training_length מייצג פתיחות למסלול לימודים ארוך: 1=פתוח, 0=מעדיף מסלול קצר.
  אסור להציג זאת כמגבלה/חסם.

חסמים:
- מקור החסמים היחיד הוא dream_barrier_choice.
- אם dream_barrier_choice מציין "אין חסם משמעותי" — אל תיצור סעיף חסמים ואל תרמוז על חסמים סמויים.

מבנה הדו״ח (בעברית):
1) סיכום קצר אך מהותי (2–4 משפטים, לא כללי)
2) על מה מבוססת ההמלצה (RIASEC + חלום/ערך/פעולה + העדפות אקדמיות, עם נימוק)
3) פירוש הנתונים:
   - RIASEC: 2–4 נקודות על נטיות מרכזיות ומה הן אומרות על סוג תחומים מתאימים
   - חלום + Value + Action: שיקוף קצר למה זה מושך ומה סוג העשייה
   - התאמה אקדמית: נוחות מתמטית + פתיחות למסלול ארוך כהתאמה בלבד
4) חסם מוצהר (רק אם קיים, ובהקשר ברור)
5) המלצות לתחומי לימוד (3 תחומים):
   - לכל תחום: 1–2 משפטים שמקושרים במפורש לנתונים
6) צעדים הבאים (3 צעדים קונקרטיים וריאליים)

שפה וסגנון:
- עברית בלבד.
- ענייני, מקצועי וחם, אך לא "מטפל".
- לא כללי, לא שיווקי.
- אם חסר מידע מסוים, ציין שחסר במקום לנחש.


        """.strip()

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"להלן נתוני המשתמש (קלט מובנה):\n\n{ai_context}"},
                ],
                model=self.model,
                temperature=0.35,
                max_tokens=2200,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI request failed: {str(e)}"

    # ---------------------------
    # One guided follow-up
    # ---------------------------
    def generate_followup(self, followup_context: str) -> str:
        """Generate a single guided follow-up answer."""

        ok, err = self._ensure_client()
        if not ok:
            return err

        system_prompt = """
אתה StudyCompass Report Generator.

מטרה:
להפיק דו״ח מסכם, שקוף, מקצועי ולא-פסיכולוגי לבחירת תחום לימודים.

עקרונות מחייבים:
1) אין להמציא חסמים, קשיים, פחדים, מגבלות או אבחנות.
2) אין לבצע ניתוח פסיכולוגי/טיפולי.
3) כל טענה חייבת להישען במפורש על נתון שהתקבל בקלט.
4) חסמים מותר לציין רק אם קיימים בנתון dream_barrier_choice.
5) אל תתמקד בשכר / כסף בדו״ח הראשי. אם מופיע נתון שוק עבודה בקלט, התעלם ממנו בדו״ח הראשי.

הבהרה חשובה (כדי למנוע תשובות שטחיות):
- מותר ואף רצוי להסביר *מדוע* נתון מסוים מוביל להמלצה מסוימת.
- מותר לקשר בין נטיות, סוג עשייה ותחומי לימוד באופן ענייני ומנומק.
- אם חסר מידע מסוים, יש לציין זאת במפורש ולא לנחש.

פירוש שדות (קריטי):
- math_difficulty מייצג נוחות עם מתמטיקה: 1=נוחות גבוהה, 0=נוחות נמוכה.
  אסור להציג זאת כקושי/חסם.
- training_length מייצג פתיחות למסלול לימודים ארוך: 1=פתוח, 0=מעדיף מסלול קצר.
  אסור להציג זאת כמגבלה/חסם.

חסמים:
- מקור החסמים היחיד הוא dream_barrier_choice.
- אם dream_barrier_choice מציין "אין חסם משמעותי" — אל תיצור סעיף חסמים ואל תרמוז על חסמים סמויים.

מבנה הדו״ח (בעברית):
1) סיכום קצר אך מהותי (2–4 משפטים, לא כללי)
2) על מה מבוססת ההמלצה (RIASEC + חלום/ערך/פעולה + העדפות אקדמיות, עם נימוק)
3) פירוש הנתונים:
   - RIASEC: 2–4 נקודות על נטיות מרכזיות ומה הן אומרות על סוג תחומים מתאימים
   - חלום + Value + Action: שיקוף קצר למה זה מושך ומה סוג העשייה
   - התאמה אקדמית: נוחות מתמטית + פתיחות למסלול ארוך כהתאמה בלבד
4) חסם מוצהר (רק אם קיים, ובהקשר ברור)
5) המלצות לתחומי לימוד (3 תחומים):
   - לכל תחום: 1–2 משפטים שמקושרים במפורש לנתונים
6) צעדים הבאים (3 צעדים קונקרטיים וריאליים)

שפה וסגנון:
- עברית בלבד.
- ענייני, מקצועי וחם, אך לא "מטפל".
- לא כללי, לא שיווקי.
- אם חסר מידע מסוים, ציין שחסר במקום לנחש.

        """.strip()

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": followup_context},
                ],
                model=self.model,
                temperature=0.35,
                max_tokens=900,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI request failed: {str(e)}"

