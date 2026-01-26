# StudyCompass 🎓🧭

StudyCompass הוא אב־טיפוס אינטראקטיבי המסייע למשתמשים לבחור תחום לימודים באמצעות שילוב של:
- שאלון נטיות (RIASEC)
- שאלת “תחום הקסם” (Dream Question)
- העדפות לימודיות ואילוצים
- דו״ח מסכם מבוסס LLM + הרחבה מונחית אחת

המערכת מיועדת להכוונה כללית ושקופה בלבד, ואינה מהווה ייעוץ מקצועי, משפטי או מחייב.

---

## ✨ תכונות עיקריות
- זרימה מלאה מקצה לקצה (UI → Backend → דו״ח)
- שאלון אדפטיבי מבוסס RIASEC
- שילוב “תחום הקסם” (חלום, ערך, עשייה, חסם)
- מנוע התאמה דטרמיניסטי (Engine) + שכבת ניסוח LLM
- דו״ח מסכם + Follow-up אחד ומוגבל
- הפרדה מלאה בין לוגיקה, נתונים ו־AI

---

## 🧱 ארכיטקטורה כללית
- **Frontend**: HTML + TailwindCSS + JavaScript
- **Backend**: Flask (Python)
- **AI Layer**: Groq LLM (API)
- **Data**: קבצי JSON סטטיים (שאלות ותחומי לימוד)
- **Deployment**: Render (Gunicorn / WSGI)

---

## 📁 מבנה הפרויקט
```
StudyCompassV2/
├─ app.py
├─ wsgi.py
├─ engine.py
├─ ai_agent.py
├─ fields_loader.py
├─ requirements.txt
├─ index.html
├─ data/
│  ├─ study_fields.json
│  └─ career_orientation_questions_v2_locked.json
├─ .gitignore
└─ README.md
```

---

## ▶️ הרצה לוקאלית (Local Run)

### דרישות מוקדמות
- Python 3.9+
- חיבור אינטרנט (לקריאות LLM)

### התקנה
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### הגדרת משתני סביבה
צור קובץ `.env` ברוט הפרויקט:
```
GROQ_API_KEY=your_api_key_here
```

### הרצה
```bash
python app.py
```

פתח בדפדפן:
```
http://127.0.0.1:5000
```

---

## 🚀 הרצה בפרודקשן / דיפלויימנט (Render)

### פקודת הרצה בפרודקשן
```bash
gunicorn wsgi:app
```

### משתני סביבה (Render Dashboard)
- `GROQ_API_KEY` – מפתח ה־LLM

### Live Demo
```
https://<your-render-app-name>.onrender.com
```

---

## 🔐 אבטחה וניהול סודות
- מפתחות API **אינם** מאוחסנים בקוד
- קובץ `.env` מוחרג מ־Git
- סודות מנוהלים דרך Render Environment Variables

---

## 🤖 שימוש ב־LLM
- ה־LLM משמש לניסוח והסבר בלבד
- כל החלטה/המלצה מתקבלת ע״י מנוע דטרמיניסטי
- אין ניתוח פסיכולוגי או הבטחות תעסוקה

---

## 📊 מגבלות ידועות
- State נשמר בזיכרון (משתמש אחד בכל רגע)
- המערכת מיועדת להכוונה כללית בלבד
- איכות התוצאה תלויה בקלט המשתמש

---

## 📝 הערה אקדמית
StudyCompass פותח כפרויקט קורס אקדמי ומטרתו להדגים:
- תכנון מערכת Human-AI
- הפרדה בין לוגיקה, נתונים ו־LLM
- דיפלויימנט מלא של אב־טיפוס עובד

---

## 👤 מחבר
פותח ע״י  
**Amit Eliezer**  **Alon Krichley**
Technion – Israel Institute of Technology
