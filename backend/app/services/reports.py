"""PDF report generation: nutrition summary, diet plan, and weight history."""

import os
from datetime import date

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
DAYS_ES = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
GOAL_ES = {
    Goal.LOSE: "Perder grasa",
    Goal.MAINTAIN: "Mantener peso",
    Goal.GAIN: "Ganar musculo",
}

BRAND = (22, 163, 74)
DARK = (50, 50, 50)
GRAY = (120, 120, 120)
LIGHT_GRAY = (230, 230, 230)

_DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_USE_UNICODE = os.path.isfile(_DEJAVU) and os.path.isfile(_DEJAVU_BOLD)
FONT = "DejaVu" if _USE_UNICODE else "Helvetica"


class NutriReport(FPDF):
    """Styled PDF report for NutriBot."""

    def __init__(self, user: User, profile: NutritionProfile | None):
        super().__init__()
        self.user = user
        self.profile = profile
        self.set_auto_page_break(auto=True, margin=20)
        if _USE_UNICODE:
            self.add_font(FONT, "", _DEJAVU, uni=True)
            self.add_font(FONT, "B", _DEJAVU_BOLD, uni=True)

    def _txt(self, style: str, size: int, color: tuple = DARK):
        self.set_font(FONT, style, size)
        self.set_text_color(*color)

    def _section(self, title: str):
        self._txt("B", 14)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BRAND)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def _kv(self, key: str, value: str, w: float = 55):
        self._txt("", 10, GRAY)
        self.cell(w, 7, key)
        self._txt("B", 10)
        self.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")

    def _macro_bar(self, label: str, cur: float, target: float | None, unit: str):
        self._txt("", 10, GRAY)
        self.cell(45, 7, label)
        self._txt("B", 11)
        val = f"{cur:.0f}"
        if target:
            val += f" / {target:.0f}"
        self.cell(40, 7, f"{val} {unit}")
        if target and target > 0:
            pct = min(cur / target, 1.0)
            bar_w = 80
            self.set_fill_color(*LIGHT_GRAY)
            self.rect(self.get_x(), self.get_y() + 1.5, bar_w, 4, "F")
            self.set_fill_color(*BRAND)
            self.rect(self.get_x(), self.get_y() + 1.5, bar_w * pct, 4, "F")
            self.set_x(self.get_x() + bar_w + 3)
            self._txt("", 9, GRAY)
            self.cell(0, 7, f"({pct:.0%})", new_x="LMARGIN", new_y="NEXT")
        else:
            self.ln(7)

    def header(self):
        if self.page_no() == 1:
            self.set_fill_color(*BRAND)
            self.rect(0, 0, 210, 55, "F")
            self.set_y(18)
            self._txt("B", 26, (255, 255, 255))
            self.cell(0, 12, "NutriBot", align="C", new_x="LMARGIN", new_y="NEXT")
            self._txt("", 13, (255, 255, 255))
            self.cell(0, 8, "Informe nutricional", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_y(60)
        else:
            self._txt("", 9, GRAY)
            self.cell(0, 6, f"NutriBot - {self.user.full_name or 'Usuario'}", align="R")
            self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
            self.ln(8)

    def footer(self):
        self.set_y(-18)
        self._txt("", 8, GRAY)
        today = date.today().strftime("%d/%m/%Y")
        self.cell(0, 10, f"Generado el {today}  |  Pagina {self.page_no()}/{{nb}}", align="C")


def generate_report_pdf(
    user: User,
    profile: NutritionProfile | None,
    daily_summary: dict,
    diet_items: list[DietPlanItem],
    weight_history: list[WeightLog],
) -> bytes:
    pdf = NutriReport(user, profile)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf._section("Datos del perfil")
    pdf._kv("Nombre", user.full_name or "-")
    if profile:
        pdf._kv("Objetivo", GOAL_ES.get(profile.goal, "-") if profile.goal else "-")
        pdf._kv("Peso actual", f"{profile.current_weight_kg} kg" if profile.current_weight_kg else "-")
        pdf._kv("Peso objetivo", f"{profile.target_weight_kg} kg" if profile.target_weight_kg else "-")
        pdf._kv("Altura", f"{profile.height_cm} cm" if profile.height_cm else "-")
        pdf._kv("Actividad", profile.activity_level.value if profile.activity_level else "-")
    pdf.ln(4)

    pdf._section("Resumen de hoy")
    totals = daily_summary.get("totals", {})
    targets = daily_summary.get("targets") or {}
    pdf._macro_bar("Calorias", totals.get("calories", 0), targets.get("calories"), "kcal")
    pdf._macro_bar("Proteina", totals.get("protein_g", 0), targets.get("protein_g"), "g")
    pdf._macro_bar("Carbohidratos", totals.get("carbs_g", 0), targets.get("carbs_g"), "g")
    pdf._macro_bar("Grasas", totals.get("fat_g", 0), targets.get("fat_g"), "g")
    pdf._macro_bar("Fibra", totals.get("fiber_g", 0), targets.get("fiber_g"), "g")
    pdf._macro_bar(
        "Agua",
        daily_summary.get("water_ml", 0),
        daily_summary.get("water_target_ml"),
        "ml",
    )
    pdf.ln(4)

    pdf._section("Plan de dieta")
    if diet_items:
        cur_date = None
        for item in diet_items:
            if item.scheduled_date != cur_date:
                cur_date = item.scheduled_date
                if cur_date:
                    ds = cur_date.strftime("%d/%m/%Y")
                    dw = DAYS_ES[cur_date.weekday()]
                    pdf._txt("B", 11, BRAND)
                    pdf.cell(0, 8, f"{dw} {ds}", new_x="LMARGIN", new_y="NEXT")

            meal_label = MEAL_ES.get(item.meal_type, "") if item.meal_type else ""
            time_str = f" ({item.scheduled_time.strftime('%H:%M')})" if item.scheduled_time else ""
            status_str = "V" if item.status == DietItemStatus.CONFIRMED else "O"

            pdf._txt("", 10)
            prefix = f"  {status_str} {meal_label}{time_str}: " if meal_label else f"  {status_str} "
            pdf.cell(0, 7, f"{prefix}{item.title}", new_x="LMARGIN", new_y="NEXT")

            macros = []
            if item.calories:
                macros.append(f"{float(item.calories):.0f} kcal")
            if item.protein_g:
                macros.append(f"P {float(item.protein_g):.0f}g")
            if item.carbs_g:
                macros.append(f"C {float(item.carbs_g):.0f}g")
            if item.fat_g:
                macros.append(f"G {float(item.fat_g):.0f}g")
            if item.fiber_g:
                macros.append(f"Fibra {float(item.fiber_g):.0f}g")
            if macros:
                pdf.set_x(pdf.l_margin + 10)
                pdf._txt("", 8, GRAY)
                pdf.cell(0, 6, " | ".join(macros), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf._txt("", 10, GRAY)
        pdf.cell(0, 7, "No hay comidas planificadas aun.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if weight_history:
        pdf._section("Historial de peso")
        pdf._txt("", 10, GRAY)
        pdf.cell(60, 7, "Fecha")
        pdf.cell(40, 7, "Peso (kg)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*LIGHT_GRAY)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(2)
        for w in weight_history[-14:]:
            pdf._txt("", 10)
            date_str = w.logged_at.strftime("%d/%m/%Y")
            pdf.cell(60, 7, date_str)
            pdf._txt("B", 10)
            pdf.cell(40, 7, f"{float(w.weight_kg):.1f}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_draw_color(*LIGHT_GRAY)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
    pdf._txt("", 8, GRAY)
    pdf.multi_cell(0, 5,
        "Este informe es orientativo y no sustituye el consejo de un profesional "
        "sanitario. NutriBot es un asistente nutricional, no un medico ni dietista colegiado."
    )

    return bytes(pdf.output())
