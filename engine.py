# =========================
# engine.py  — StudyCompassEngine
# =========================
import math
from typing import List, Dict, Any, Optional, Tuple


class StudyCompassEngine:
    """
    Adaptive StudyCompass Engine
    - Warm-start + Focus + Early-stop (adaptive questionnaire)
    - FIX #1: Social-asymmetric distance (social low doesn't kill tech/science)
    - FIX #2: Diversity reranking for Top-N (presentation)
    - FIX #3: Hybrid bonus for bridge fields when user is high on BOTH social and science axes
    """

    SCORING_WEIGHTS = {
        "penalty_factor": 0.25,
        "value_boost_factor": 0.07,
        "max_distance": math.sqrt(6),
    }

    DIMS = ["analytical", "investigative", "social", "creative", "enterprising", "hands_on"]

    ADAPTIVE = {
        "nmax_questions": 18,
        "k_focus": 3,
        "min_per_dim_warmstart": 1,
        "min_per_top_dim": 4,
        "gap_threshold": 0.15,
        "stability_window": 3,
        "max_same_dim_streak": 2,
        "social_subdim_diversity_boost": 1.5,
    }

    SOCIAL_ASYMMETRIC = {
        "enabled": True,
        "weight": 0.7,
    }

    DIVERSITY = {
        "enabled": True,
        "top_n": 3,
        "max_per_group_in_top_n": 1,
        "min_score_ratio": 0.92,
    }

    # FIX #3: Hybrid bonus knobs
    HYBRID = {
        "enabled": True,
        "tag": "hybrid_social_science",
        "bonus": 0.05,           # small! just enough to surface bridge fields
        "min_social": 0.75,      # user social high
        "min_science": 0.75,     # user analytical OR investigative high
    }

    def __init__(self, fields: List[Dict[str, Any]], questions: List[Dict[str, Any]]):
        self.fields = fields
        self.questions = questions

        self.user_profile: Dict[str, float] = {d: 0.5 for d in self.DIMS}
        self.answered_ids: List[str] = []

        self.dim_counts: Dict[str, int] = {d: 0 for d in self.DIMS}
        self.dim_sums: Dict[str, float] = {d: 0.0 for d in self.DIMS}
        self.last_dims: List[str] = []
        self.top_history: List[Tuple[str, str]] = []

        self.sub_dim_counts: Dict[str, int] = {}

    # -------------------------
    # Adaptive questionnaire helpers
    # -------------------------
    def _primary_dimension(self, q: Dict[str, Any]) -> Optional[str]:
        dim = q.get("dimension")
        if dim in self.user_profile:
            return dim

        impacts = q.get("impact", {})
        if not impacts:
            return None

        best_dim = None
        best_abs_w = -1.0
        for d, w in impacts.items():
            if d in self.user_profile:
                aw = abs(float(w))
                if aw > best_abs_w:
                    best_abs_w = aw
                    best_dim = d
        return best_dim

    def _unanswered_questions(self) -> List[Dict[str, Any]]:
        answered = set(self.answered_ids)
        return [
            q for q in self.questions
            if q.get("id") not in answered and q.get("status", "active") == "active"
        ]

    def _current_top(self) -> Tuple[str, str, float]:
        ranked = sorted(self.user_profile.items(), key=lambda kv: kv[1], reverse=True)
        top1, s1 = ranked[0]
        top2, s2 = ranked[1]
        return top1, top2, (s1 - s2)

    def _is_stable(self) -> bool:
        w = self.ADAPTIVE["stability_window"]
        if len(self.top_history) < w:
            return False
        tail = self.top_history[-w:]
        return all(pair == tail[0] for pair in tail)

    def _should_stop(self) -> bool:
        if len(self.answered_ids) >= self.ADAPTIVE["nmax_questions"]:
            return True

        if any(self.dim_counts[d] < self.ADAPTIVE["min_per_dim_warmstart"] for d in self.DIMS):
            return False

        _, _, gap = self._current_top()

        if self._is_stable() and gap >= self.ADAPTIVE["gap_threshold"]:
            return True

        k = self.ADAPTIVE["k_focus"]
        topk = [d for d, _ in sorted(self.user_profile.items(), key=lambda kv: kv[1], reverse=True)[:k]]
        if all(self.dim_counts[d] >= self.ADAPTIVE["min_per_top_dim"] for d in topk):
            return True

        return False

    def _dim_streak_block(self) -> Optional[str]:
        if not self.last_dims:
            return None
        streak_dim = self.last_dims[-1]
        streak_len = 1
        for i in range(len(self.last_dims) - 2, -1, -1):
            if self.last_dims[i] == streak_dim:
                streak_len += 1
            else:
                break
        return streak_dim if streak_len >= self.ADAPTIVE["max_same_dim_streak"] else None

    def get_next_question(self) -> Optional[Dict[str, Any]]:
        if self._should_stop():
            return None

        pool = self._unanswered_questions()
        if not pool:
            return None

        # Warm-start coverage
        missing_dims = [d for d in self.DIMS if self.dim_counts[d] < self.ADAPTIVE["min_per_dim_warmstart"]]
        if missing_dims:
            for d in missing_dims:
                for q in pool:
                    if self._primary_dimension(q) == d:
                        return q

        # Focus mode
        top1, top2, gap = self._current_top()
        k = self.ADAPTIVE["k_focus"]
        topk = [d for d, _ in sorted(self.user_profile.items(), key=lambda kv: kv[1], reverse=True)[:k]]
        target_dims = {top1, top2} if gap < self.ADAPTIVE["gap_threshold"] else set(topk)

        block_dim = self._dim_streak_block()

        best_q = None
        best_score = -1e9

        for q in pool:
            d = self._primary_dimension(q)
            if d is None:
                continue

            score = 0.0
            if d in target_dims:
                score += 10.0

            score += 2.0 * (1.0 / (1 + self.dim_counts[d]))

            if d in (top1, top2) and gap < self.ADAPTIVE["gap_threshold"]:
                score += 3.0 * (1.0 / (1 + self.dim_counts[d]))

            if block_dim is not None and d == block_dim:
                score -= 5.0

            if d == "social":
                sub = q.get("sub_dimension")
                if sub:
                    score += self.ADAPTIVE["social_subdim_diversity_boost"] * (
                        1.0 / (1 + self.sub_dim_counts.get(sub, 0))
                    )

            if "dimension" in q:
                score += 0.2

            if score > best_score:
                best_score = score
                best_q = q

        return best_q if best_q is not None else pool[0]

    def update_profile(self, question_id: str, value: float):
        question = next((q for q in self.questions if q.get("id") == question_id), None)
        if not question:
            return

        impacts = question.get("impact", {})
        for dimension, weight in impacts.items():
            if dimension in self.user_profile:
                current = self.user_profile[dimension]
                w = float(weight)
                self.user_profile[dimension] = (current + (float(value) * w)) / (1 + w)

        if question_id not in self.answered_ids:
            self.answered_ids.append(question_id)

        primary_dim = self._primary_dimension(question)
        if primary_dim in self.user_profile:
            self.dim_counts[primary_dim] += 1
            self.dim_sums[primary_dim] += float(value)
            self.last_dims.append(primary_dim)

        sub = question.get("sub_dimension")
        if sub:
            self.sub_dim_counts[sub] = self.sub_dim_counts.get(sub, 0) + 1

        top1, top2, _ = self._current_top()
        self.top_history.append((top1, top2))

    # -------------------------
    # Diversity rerank helpers
    # -------------------------
    def _field_group(self, field: Dict[str, Any]) -> str:
        if "family" in field and field["family"]:
            return str(field["family"])
        interests = field.get("interests", {})
        if not interests:
            return "unknown"
        best_dim = max(interests.items(), key=lambda kv: kv[1])[0]
        return f"dom_{best_dim}"

    def _diversify_top_n(self, ranked: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
        if n <= 1 or len(ranked) <= 1:
            return ranked

        best_score = ranked[0]["match_score"]
        thresh = best_score * self.DIVERSITY["min_score_ratio"]
        candidates = [r for r in ranked if r["match_score"] >= thresh]
        tail = [r for r in ranked if r["match_score"] < thresh]

        selected: List[Dict[str, Any]] = []
        used_groups: Dict[str, int] = {}

        def group_of(rec: Dict[str, Any]) -> str:
            return rec.get("_group", "unknown")

        for _ in range(min(n, len(candidates))):
            pick = None
            for rec in candidates:
                g = group_of(rec)
                if used_groups.get(g, 0) < self.DIVERSITY["max_per_group_in_top_n"]:
                    pick = rec
                    break
            if pick is None:
                pick = candidates[0]

            selected.append(pick)
            used_groups[group_of(pick)] = used_groups.get(group_of(pick), 0) + 1
            candidates.remove(pick)

        return selected + candidates + tail

    # -------------------------
    # Recommendations (FIX #1 + FIX #2 + FIX #3)
    # -------------------------
    def get_recommendations(
        self,
        user_constraints: Optional[Dict[str, float]] = None,
        selected_values: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        recommendations = []

        user_social = self.user_profile.get("social", 0.5)
        user_science = max(self.user_profile.get("analytical", 0.5),
                           self.user_profile.get("investigative", 0.5))

        hybrid_active = (
            self.HYBRID["enabled"]
            and user_social >= self.HYBRID["min_social"]
            and user_science >= self.HYBRID["min_science"]
        )

        for field in self.fields:
            interests = field.get("interests", {})

            # 1) Interest score with FIX #1 (social-asymmetric)
            dist_sq = 0.0
            for d in self.user_profile:
                u = self.user_profile[d]
                f = interests.get(d, 0.5)

                if self.SOCIAL_ASYMMETRIC["enabled"] and d == "social":
                    diff = max(0.0, f - u)
                    w = float(self.SOCIAL_ASYMMETRIC["weight"])
                else:
                    diff = (u - f)
                    w = 1.0

                dist_sq += w * (diff ** 2)

            distance = math.sqrt(dist_sq)
            interest_score = max(0.0, 1.0 - (distance / self.SCORING_WEIGHTS["max_distance"]))

            # 2) Constraints penalty
            penalty = 0.0
            if user_constraints:
                for k, user_val in user_constraints.items():
                    required = field.get("constraints", {}).get(k, 0.5)
                    if required > user_val:
                        penalty += (required - user_val) * self.SCORING_WEIGHTS["penalty_factor"]

            # 3) Values bonus
            matched_v = []
            bonus = 0.0
            if selected_values:
                core_vals = field.get("core_values", [])
                matched_v = [v for v in selected_values if v in core_vals]
                bonus = len(matched_v) * self.SCORING_WEIGHTS["value_boost_factor"]

            final_score = max(0.0, min(1.0, (interest_score - penalty) + bonus))

            # FIX #3: Hybrid bonus for bridge fields (small, conditional)
            if hybrid_active:
                tags = field.get("tags", [])
                if isinstance(tags, list) and (self.HYBRID["tag"] in tags):
                    final_score = min(1.0, final_score + float(self.HYBRID["bonus"]))

            rec = {
                "id": field["id"],
                "name": field["name"],
                "match_score": round(final_score * 100, 2),
                "matched_values": matched_v,
            }
            rec["_group"] = self._field_group(field)  # for diversity
            recommendations.append(rec)

        ranked = sorted(recommendations, key=lambda x: x["match_score"], reverse=True)

        # FIX #2: diversify top-N (presentation only)
        if self.DIVERSITY["enabled"]:
            ranked = self._diversify_top_n(ranked, self.DIVERSITY["top_n"])

        # remove internal
        for r in ranked:
            r.pop("_group", None)

        return ranked

    # -------------------------
    # AI Context (Final report)
    # -------------------------
    def get_full_context_for_ai(
        self,
        dream_data: Dict[str, Any],
        constraints: Dict[str, Any],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """
        Build a safe, grounded Hebrew context for the LLM final report.
        IMPORTANT: report must NOT focus on salary and must not invent barriers.
        """

        # Extract dream structured fields (may be missing in some flows)
        dream_title = dream_data.get("title") or ""
        dream_free_text = dream_data.get("free_text") or dream_data.get("dream_free_text") or ""
        dream_value_choice = dream_data.get("dream_value_choice") or dream_data.get("value_choice") or ""
        dream_action_choice = dream_data.get("dream_action_choice") or dream_data.get("action_choice") or ""
        dream_barrier_choice = dream_data.get("dream_barrier_choice") or dream_data.get("barrier_choice") or ""

        # Constraints are FIT signals (not emotional barriers)
        math_fit = constraints.get("math_difficulty", None)
        length_fit = constraints.get("training_length", None)

        ctx: List[str] = []
        ctx.append("STUDYCOMPASS — נתוני משתמש (לדו״ח מסכם)\n")

        ctx.append("1) פרופיל נטיות (RIASEC/6 ממדים, 0–1):")
        ctx.append(str(self.user_profile))
        ctx.append(f"שאלות שנענו: {len(self.answered_ids)}\n")

        ctx.append("2) החלום (Dream Question) + פירוט מובנה:")
        ctx.append(f"- dream_title: {dream_title}")
        if dream_free_text:
            ctx.append(f"- dream_free_text: {dream_free_text}")
        ctx.append(f"- dream_value_choice: {dream_value_choice}")
        ctx.append(f"- dream_action_choice: {dream_action_choice}")
        ctx.append(f"- dream_barrier_choice: {dream_barrier_choice}\n")

        ctx.append("3) העדפות אקדמיות (FIT בלבד — לא חסמים):")
        ctx.append(f"- math_difficulty: {math_fit}")
        ctx.append(f"- training_length: {length_fit}\n")

        ctx.append("הגדרות סמנטיות מחייבות (ANTI-INVERSION):")
        ctx.append("- math_difficulty = נוחות עם מתמטיקה (1=נוחות גבוהה, 0=נוחות נמוכה). זה לא 'קושי'.")
        ctx.append("- training_length = פתיחות למסלול ארוך (1=פתוח, 0=מעדיף קצר). זה לא 'מגבלה'.")
        ctx.append("- חסמים בדו״ח מותרים רק מתוך dream_barrier_choice. אם אין חסם משמעותי—לא לציין חסמים.\n")

        ctx.append("4) Top-3 המלצות מהמנוע (דירוג בסיסי כבר מחושב, לא לשנות אותו):")
        for i, rec in enumerate(recommendations[:3], start=1):
            ctx.append(
                f"{i}. {rec['name']} — match_score: {rec['match_score']}% — matched_values: {rec.get('matched_values', [])}"
            )

        return "\n".join(ctx)

    # -------------------------
    # Follow-up helpers (ONE guided question)
    # -------------------------
    def _salary_label(self, salary_potential: Optional[float]) -> str:
        """
        Map numeric [0,1] to ONLY: גבוה / בינוני / נמוך (no numbers, no extra words).
        """
        if salary_potential is None:
            return "אין נתון"
        try:
            x = float(salary_potential)
        except Exception:
            return "אין נתון"

        if x >= 0.75:
            return "גבוה"
        if x >= 0.45:
            return "בינוני"
        return "נמוך"

    def _field_by_name(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Find field dict by its displayed name."""
        target = str(field_name).strip()
        for f in self.fields:
            if str(f.get("name", "")).strip() == target:
                return f
        return None

    def get_followup_context_for_ai(
        self,
        followup_type: str,
        selection: str,
        dream_title: str,
        recommendations: List[Dict[str, Any]],
    ) -> str:
        """
        Build a constrained context for ONE guided follow-up.

        followup_type examples:
          - "expand_recommendation"
          - "expand_dream"
          - "market_info"

        selection:
          - "1"/"2"/"3" for recommendations
          - "dream"
        """

        # pick target
        target_name = None
        target_rec = None

        if followup_type == "expand_dream" or selection == "dream":
            target_name = dream_title.strip() or "תחום החלום"
        else:
            try:
                idx = int(selection) - 1
            except Exception:
                idx = 0
            idx = max(0, min(2, idx))
            target_rec = recommendations[idx] if recommendations and len(recommendations) > idx else None
            target_name = (target_rec.get("name") if target_rec else "תחום מומלץ").strip()

        # Salary info for ALL followups (label only: גבוה/בינוני/נמוך; no numbers)
        salary_section_lines: List[str] = []
        f = self._field_by_name(target_name)

        salary_section_lines.append("מידע כללי (השתכרות):")
        if f:
            salary_section_lines.append(f"- פוטנציאל השתכרות: {self._salary_label(f.get('salary_potential', None))}")
            salary_section_lines.append("- הערה: מדובר בתיאור איכותי בלבד מתוך הדאטה, ולא הבטחה אישית או נתון כספי.")
        else:
            salary_section_lines.append("- פוטנציאל השתכרות: אין נתון")
            salary_section_lines.append("- הערה: תחום זה לא ממופה אצלנו לדאטה עם תיאור פוטנציאל השתכרות, ולכן אין להסיק או לנחש.")

        ctx: List[str] = []
        ctx.append("STUDYCOMPASS — Follow-up (שאלה מונחית אחת)")
        ctx.append(f"followup_type: {followup_type}")
        ctx.append(f"target_field: {target_name}\n")

        ctx.append("הנחיה לתשובה:")
        if followup_type == "expand_recommendation":
            ctx.append("- תן הרחבה על התחום הנבחר: מה לומדים, למי זה מתאים, דוגמאות תפקידים, ואיך לבדוק התאמה בשבוע הקרוב.")
        elif followup_type == "market_info":
            ctx.append("- תן הרחבה ניטרלית על שוק העבודה/יציבות/מסלולי כניסה. אל תתן מספרים בש״ח.")
        else:  # expand_dream
            ctx.append("- תן הרחבה על תחום החלום: וריאציות לימודיות, מסלולי כניסה, ומה אפשר לעשות כדי לבדוק התאמה בלי להתחייב.")

        ctx.append("")  # spacing
        ctx.extend(salary_section_lines)

        return "\n".join(ctx)


# =========================
# ai_agent.py — CareerAIAgent (Groq)
# =========================
import os
from groq import Groq
from dotenv import load_dotenv

# Load .env for local development (Render provides env vars directly)
load_dotenv()


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

    def generate_followup(self, followup_context: str, followup_type: str) -> str:
        """
        Generate a single guided follow-up answer.

        followup_type is accepted for consistency/logging,
        but the same rules apply to all followups now (including salary rule).
        """
        ok, err = self._ensure_client()
        if not ok:
            return err

        _ = (followup_type or "").strip()

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



