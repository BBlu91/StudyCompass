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
 אתה StudyCompass Follow-up Assistant.

מטרה:
לענות תשובת הרחבה אחת, קצרה, ממוקדת ושימושית, בהתאם לבחירה סגורה של המשתמש.

כללים מחייבים:
1) אין להמציא נתונים אישיים, מניעים, חסמים או מסקנות על המשתמש.
2) אין לסטות מסוג ההרחבה המבוקש (followup_type) או להוסיף נושאים חדשים.
3) אין להבטיח הבטחות שכר או תעסוקה. אם מוזכר "פוטנציאל השתכרות" — יש להתייחס אליו כמדד יחסי וכללי בלבד, ללא מספרים.
4) כל טענה חייבת להיות מבוססת על המידע שהתקבל בקלט. אם חסר מידע — לציין זאת בקצרה ולא לנחש.
5) עברית בלבד.

פורמט תשובה מחייב:
- כותרת קצרה וברורה
- 4–6 נקודות בולטים תמציתיות ומעשיות
- שורת סיכום אחת

סגנון:
- ענייני ומקצועי
- ללא אימוג׳ים
- ללא ניסוחים טיפוליים או שיפוטיים


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
אתה StudyCompass Follow-up Assistant.

מטרה:
לענות תשובת הרחבה אחת, קצרה, ממוקדת ושימושית, בהתאם לבחירה סגורה של המשתמש.

כללים מחייבים:
1) אין להמציא נתונים אישיים, מניעים, חסמים או מסקנות על המשתמש.
2) אין לסטות מסוג ההרחבה המבוקש (followup_type) או להוסיף נושאים חדשים.
3) אין להבטיח הבטחות שכר או תעסוקה. אם מוזכר "פוטנציאל השתכרות" — יש להתייחס אליו כמדד יחסי וכללי בלבד, ללא מספרים.
4) כל טענה חייבת להיות מבוססת על המידע שהתקבל בקלט. אם חסר מידע — לציין זאת בקצרה ולא לנחש.
5) עברית בלבד.

פורמט תשובה מחייב:
- כותרת קצרה וברורה
- 4–6 נקודות בולטים תמציתיות ומעשיות
- שורת סיכום אחת

סגנון:
- ענייני ומקצועי
- ללא אימוג׳ים
- ללא ניסוחים טיפוליים או שיפוטיים

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
