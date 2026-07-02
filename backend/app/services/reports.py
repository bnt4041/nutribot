"""PDF report generation: nutrition summary, diet plan, and weight history."""

import io
from datetime import date, datetime

from fpdf import FPDF

from app.models.diet_plan import DietPlanItem
from app.models.enums import DietItemStatus, Goal, MealType
from app.models.nutrition_profile import NutritionProfile
from app.models.user import User
from app.models.weight_log import WeightLog

MEAL_ES = {
    MealType.BREAKFAST: "Desayuno",
    MealType.LUNCH: "Comida",
    MealType.DINNER: "Cena",
    MealType.SNACK: "Snack",
}
DAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
GOAL_ES = {
    Goal.LOSE: "Perder grasa",
    Goal.MAINTAIN: "Mantener peso",
    Goal.GAIN: "Ganar músculo",
}

BRAND = (22, 163, 74)  # green-600
DARK = (50, 50, 50)
GRAY = (120, 120, 120)
LIGHT_GRAY = (230, 230, 230)


class NutriReport(FPDF):
    """Styled PDF report for NutriBot."""

    def __init__(self, user: User, profile: NutritionProfile | None):
        super().__init__()
        self.user = user
        self.profile = profile
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            # Title page header
            self.set_fill_color(*BRAND)
            self.rect(0, 0, 210, 55, "F")
            self.set_y(18)
            self.set_font("Helvetica", "B", 28)
            self.set_text_color(255, 255, 255)
            self.cell(0, 12, "🥗  NutriBot", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 13)
            self.cell(0, 8, "Informe nutricional", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_y(60)
        else:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(*GRAY)
            self.cell(0, 6, f"NutriBot — {self.user.full_name or 'Usuario'}", align="R")
            self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
            self.ln(8)

    def footer(self):
        self.set_y(-18)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 10, f"Generado el {date.today().strftime('%d/%m/%Y')}  |  Página {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*DARK)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        # Green underline
        self.set_draw_color(*BRAND)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def key_value(self, key: str, value: str, w_key: float = 55):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*GRAY)
        self.cell(w_key, 7, key)
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")

    def macro_row(self, label: str, current: float, target: float | None, unit: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*GRAY)
        self.cell(45, 7, label)
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "B", 11)
        val = f"{current:.0f}"
        if target:
            val += f" / {target:.0f}"
        self.cell(40, 7, f"{val} {unit}")
        # Progress bar
        if target and target > 0:
            pct = min(current / target, 1.0)
            bar_w = 80
            self.set_fill_color(*LIGHT_GRAY)
            self.rect(self.get_x(), self.get_y() + 1.5, bar_w, 4, "F")
            self.set_fill_color(*BRAND)
            self.rect(self.get_x(), self.get_y() + 1.5, bar_w * pct, 4, "F")
            self.set_x(self.get_x() + bar_w + 3)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*GRAY)
            self.cell(0, 7, f"({pct:.0%})", new_x="LMARGIN", new_y="NEXT")
        else:
            self.ln(7)


def generate_report_pdf(
    user: User,
    profile: NutritionProfile | None,
    daily_summary: dict,
    diet_items: list[DietPlanItem],
    weight_history: list[WeightLog],
) -> bytes:
    """Generate a full nutrition report PDF and return the bytes."""
    pdf = NutriReport(user, profile)
    pdf.alias_nb_pages()
    pdf.add_page()

    # ── 1. Profile ──────────────────────────────────────────────────────
    pdf.section_title("👤  Datos del perfil")
    pdf.key_value("Nombre", user.full_name or "—")
    if profile:
        pdf.key_value("Objetivo", GOAL_ES.get(profile.goal, "—") if profile.goal else "—")
        pdf.key_value("Peso actual", f"{profile.current_weight_kg} kg" if profile.current_weight_kg else "—")
        pdf.key_value("Peso objetivo", f"{profile.target_weight_kg} kg" if profile.target_weight_kg else "—")
        pdf.key_value("Altura", f"{profile.height_cm} cm" if profile.height_cm else "—")
        pdf.key_value("Actividad", profile.activity_level.value if profile.activity_level else "—")
    pdf.ln(4)

    # ── 2. Today's summary ──────────────────────────────────────────────
    pdf.section_title("📊  Resumen de hoy")
    totals = daily_summary.get("totals", {})
    targets = daily_summary.get("targets") or {}
    pdf.macro_row("Calorías", totals.get("calories", 0), targets.get("calories"), "kcal")
    pdf.macro_row("Proteína", totals.get("protein_g", 0), targets.get("protein_g"), "g")
    pdf.macro_row("Carbohidratos", totals.get("carbs_g", 0), targets.get("carbs_g"), "g")
    pdf.macro_row("Grasas", totals.get("fat_g", 0), targets.get("fat_g"), "g")
    pdf.ln(4)

    # ── 3. Diet plan ────────────────────────────────────────────────────
    pdf.section_title("🥗  Plan de dieta")
    if diet_items:
        current_date = None
        for item in diet_items:
            if item.scheduled_date != current_date:
                current_date = item.scheduled_date
                if current_date:
                    ds = current_date.strftime("%d/%m/%Y")
                    dw = DAYS_ES[current_date.weekday()]
                    pdf.set_font("Helvetica", "B", 11)
                    pdf.set_text_color(*BRAND)
                    pdf.cell(0, 8, f"{dw} {ds}", new_x="LMARGIN", new_y="NEXT")

            meal_label = MEAL_ES.get(item.meal_type, "") if item.meal_type else ""
            time_str = f" ({item.scheduled_time.strftime('%H:%M')})" if item.scheduled_time else ""
            status_str = "✓" if item.status == DietItemStatus.CONFIRMED else "○"

            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*DARK)
            prefix = f"  {status_str} {meal_label}{time_str}: " if meal_label else f"  {status_str} "
            pdf.cell(0, 7, f"{prefix}{item.title}", new_x="LMARGIN", new_y="NEXT")

            # Macros line
            macros_parts = []
            if item.calories:
                macros_parts.append(f"{float(item.calories):.0f} kcal")
            if item.protein_g:
                macros_parts.append(f"P {float(item.protein_g):.0f}g")
            if item.carbs_g:
                macros_parts.append(f"C {float(item.carbs_g):.0f}g")
            if item.fat_g:
                macros_parts.append(f"G {float(item.fat_g):.0f}g")
            if macros_parts:
                pdf.set_x(pdf.l_margin + 10)
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*GRAY)
                pdf.cell(0, 6, " · ".join(macros_parts), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 7, "No hay comidas planificadas aún.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── 4. Weight history ───────────────────────────────────────────────
    if weight_history:
        pdf.section_title("⚖️  Historial de peso")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*GRAY)
        pdf.cell(60, 7, "Fecha")
        pdf.cell(40, 7, "Peso (kg)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*LIGHT_GRAY)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(2)

        for w in weight_history[-14:]:  # last 14 entries
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*DARK)
            date_str = w.logged_at.strftime("%d/%m/%Y")
            pdf.cell(60, 7, date_str)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(40, 7, f"{float(w.weight_kg):.1f}", new_x="LMARGIN", new_y="NEXT")

    # ── 5. Disclaimer ───────────────────────────────────────────────────
    pdf.ln(6)
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 5,
        "Este informe es orientativo y no sustituye el consejo de un profesional "
        "sanitario. NutriBot es un asistente nutricional, no un médico ni dietista "
        "colegiado."
    )

    return pdf.output()
