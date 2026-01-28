import os
import re
from groq import Groq
from dotenv import load_dotenv

# Load .env for local development (Render provides env vars directly)
load_dotenv()

# ---------------------------
# System Prompts
# ---------------------------

BASE_REPORT_SYSTEM_PROMPT = """
אתה StudyCompass Report Generator.

מטרה:
להפיק דו״ח מסכם, שקוף, מקצועי ולא-פסיכולוגי לבחירת תחום לימודים.

עקרונות מחייבים:
1) אין להמציא חסמים, קשיים, פחדים, מגבלות או אבחנות.
2) אין לבצע ניתוח פסיכולוגי/טיפולי.
3) כל טענה חייבת להישען במפורש על נתון שהתקבל בקלט.
4) חסמים מותר לציין רק אם קיימים בנתון החסם שנמסר.
5) אין להתמקד בשכר או כסף בדו״ח הראשי.

הבהרות:
- מותר להסביר מדוע נתון מסוים מוביל להמלצה מסוימת.
- אם חסר מידע, יש לציין שחסר ולא לנחש.

כללי שפה ופלט:
- עברית בלבד.
- כתיבה עניינית, מקצועית וברורה.
- ללא כוכביות, ללא Markdown, ללא סימונים טכניים.
- ללא שמות משתנים או מונחים באנגלית.
- אין הדגשות באמצעות סימנים; אם צריך הדגשה, להשתמש במילים כמו "חשוב:".

מגבלת אורך מחייבת:
- עד כ־450–600 מילים סך הכול.
- כל סעיף קצר וממוקד.
""".strip()


FOLLOWUP_SYSTEM_PROMPT = """
אתה StudyCompass Follow-up Generator.

מטרה:
להפיק תשובת הרחבה אחת, ממוקדת, מקצועית ומבוססת נתונים.

כללים מחייבים:
1) כל טענה חייבת להישען על נתון שמופיע בקלט.
2) אין לבצע ניתוח פסיכולוגי או להמציא חסמים.
3) אם חסר מידע — לומר זאת במפורש.

כלל שכר (חל על כל הפולואפים):
- מותר להתייחס לפוטנציאל השתכרות רק אם מופיע בקלט תיאור מילולי: גבוה / בינוני / נמוך.
- אסור לציין מספרים או סכומים כספיים.
- אם אין נתון שכר — לציין שאין מידע.

כללי פלט:
- עברית בלבד.
- ללא כוכביות או Markdown.
- ללא שמות משתנים באנגלית.
- תשובה קצרה–בינונית, מחולקת לפסקאות קריאות.
""".strip()


# ---------------------------
# AI Agent
# ---------------------------

class CareerAIAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = "llama-3.3-70b-versatile"
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def _ensure_client(self):
        if not self.client:
            return False, "GROQ_API_KEY חסר בשרת."
        return True, None

    # ---------------------------
    # Output cleaning (anti-Markdown)
    # ---------------------------
    def _clean_text(self, text: str) -> str:
        if not text:
            return ""

        t = text.strip()

        # remove markdown emphasis
        t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)
        t = re.sub(r"\*(.*?)\*", r"\1", t)

        # remove headers
        t = re.sub(r"^#{1,6}\s*", "", t, flags=re.MULTILINE)

        # remove code markers
        t = t.replace("```", "").replace("`", "")

        # normalize whitespace
        t = re.sub(r"\n{3,}", "\n\n", t)

        return t.strip()

    # ---------------------------
    # Final report
    # ---------------------------
    def generate_report(self, ai_context: str) -> str:
        ok, err = self._ensure_client()
        if not ok:
            return err

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": BASE_REPORT_SYSTEM_PROMPT},
                    {"role": "user", "content": f"להלן נתוני המשתמש:\n\n{ai_context}"},
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=1100,
            )

            raw = (response.choices[0].message.content or "").strip()
            if not raw:
                return "הדו״ח לא הופק עקב מגבלת מערכת. ניתן לנסות שוב."

            return self._clean_text(raw)

        except Exception as e:
            return f"שגיאה בהפקת הדו״ח: {str(e)}"

    # ---------------------------
    # Follow-up
    # ---------------------------
    def generate_followup(self, followup_context: str) -> str:
        ok, err = self._ensure_client()
        if not ok:
            return err

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": FOLLOWUP_SYSTEM_PROMPT},
                    {"role": "user", "content": followup_context},
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=800,
            )

            raw = (response.choices[0].message.content or "").strip()
            if not raw:
                return "לא התקבלה תשובת הרחבה."

            return self._clean_text(raw)

        except Exception as e:
            return f"שגיאה בתשובת ההרחבה: {str(e)}"


     


