import os
from groq import Groq
from dotenv import load_dotenv

# Load .env for local development (Render provides env vars directly)
load_dotenv()


# ---------------------------
# Shared system prompts
# ---------------------------

BASE_REPORT_SYSTEM_PROMPT = """
אתה StudyCompass Report Generator.

מטרה:
להפיק דו״ח מסכם, שקוף, מקצועי ולא-פסיכולוגי לבחירת תחום לימודים.

עקרונות מחייבים:
1) אין להמציא חסמים, קשיים, פחדים, מגבלות או אבחנות.
2) אין לבצע ניתוח פסיכולוגי/טיפולי.
3) כל טענה חייבת להישען במפורש על נתון שהתקבל בקלט.
4) חסמים מותר לציין רק אם קיימים בנתון dream_barrier_choice.
5) אל תתמקד בשכר / כסף בדו״ח הראשי. אם מופיע נתון שוק עבודה בקלט, התעלם ממנו בדו״ח הראשי.

הבהרה חשובה:
- מותר ואף רצוי להסביר מדוע נתון מסוים מוביל להמלצה מסוימת.
- מותר לקשר בין נטיות, סוג עשייה ותחומי לימוד באופן ענייני ומנומק.
- אם חסר מידע מסוים, יש לציין זאת במפורש ולא לנחש.

פירוש שדות (קריטי):
- נוחות מתמטית: ערך גבוה משמעו נוחות גבוהה, ערך נמוך משמעו נוחות נמוכה.
  אסור להציג זאת כקושי/חסם.
- פתיחות למסלול לימודים ארוך: ערך גבוה משמעו פתיחות, ערך נמוך משמעו העדפה למסלול קצר.
  אסור להציג זאת כמגבלה/חסם.

חסמים:
- מקור החסמים היחיד הוא dream_barrier_choice.
- אם dream_barrier_choice מציין "אין חסם משמעותי" — אל תיצור סעיף חסמים ואל תרמוז על חסמים סמויים.

מבנה הדו״ח (בעברית):
1) סיכום קצר אך מהותי (2–4 משפטים, לא כללי)
2) על מה מבוססת ההמלצה (נטיות + חלום/ערך/פעולה + העדפות אקדמיות, עם נימוק)
3) פירוש הנתונים
4) חסם מוצהר (רק אם קיים)
5) המלצות לתחומי לימוד (3 תחומים)
6) צעדים הבאים (3 צעדים קונקרטיים וריאליים)

שפה וסגנון:
- עברית בלבד.
- ענייני, מקצועי וחם, אך לא "מטפל".
- לא כללי, לא שיווקי.
- אם חסר מידע מסוים, ציין שחסר במקום לנחש.

כללי פלט מחייבים:
- ללא כוכביות או Markdown (ללא *, **, ###).
- ללא שמות משתנים / שדות באנגלית.
- כתיבה נקייה בפסקאות רגילות, קריאות, ללא סימונים טכניים.
""".strip()


FOLLOWUP_SYSTEM_PROMPT_ALL = """
אתה StudyCompass Follow-up Generator.

מטרה:
להפיק תשובת הרחבה אחת, שקופה, מקצועית ומבוססת-נתונים, בהתאם לבחירת המשתמש.

כללים מחייבים:
1) כל טענה חייבת להישען במפורש על נתון שמופיע בקלט שנשלח אליך.
2) אין לבצע ניתוח פסיכולוגי/טיפולי, ואין להמציא חסמים/פחדים/מגבלות.
3) אם חסר מידע — לומר שחסר, ולא לנחש.

כלל שכר (חל על כל הפולואפים):
- מותר להתייחס לשכר/פוטנציאל השתכרות רק אם בקלט מופיע תיאור מילולי מפורש (למשל: "גבוה/בינוני/נמוך") עבור התחום הרלוונטי.
- אסור להציג מספרים, טווחים כספיים, או להמציא נתוני שכר.
- אם אין נתון שכר בקלט עבור התחום שנשאל עליו — לומר במפורש שאין לנו נתון שכר עבורו.

כללי פלט:
- עברית בלבד.
- ללא כוכביות או Markdown.
- ללא שמות משתנים / שדות באנגלית.
- תשובה קצרה-בינונית, ברורה וקריאה בפסקאות.
""".strip()


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

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": BASE_REPORT_SYSTEM_PROMPT},
                    {"role": "user", "content": f"להלן נתוני המשתמש (קלט מובנה):\n\n{ai_context}"},
                ],
                model=self.model,
                temperature=0.35,
                max_tokens=2200,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            return f"AI request failed: {str(e)}"

    # ---------------------------
    # One guided follow-up
    # ---------------------------
    def generate_followup(self, followup_context: str, followup_type: str) -> str:
        """
        Generate a single guided follow-up answer.

        NOTE:
        followup_type is still accepted for consistency/logging,
        but the same rules apply to all followups now (including salary rule).
        """
        ok, err = self._ensure_client()
        if not ok:
            return err

        _ = (followup_type or "").strip()  # keep for future use / consistency

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": FOLLOWUP_SYSTEM_PROMPT_ALL},
                    {"role": "user", "content": followup_context},
                ],
                model=self.model,
                temperature=0.35,
                max_tokens=900,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            return f"AI request failed: {str(e)}"


