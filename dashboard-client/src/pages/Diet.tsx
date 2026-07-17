import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { StatCard } from "../components/StatCard";
import { DietPlanItem } from "../types";

const DAYS_FULL = [
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
  "Domingo",
];
const DAYS_SHORT = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const MONTHS = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];
const MEAL_ES: Record<string, string> = {
  breakfast: "Desayuno",
  lunch: "Comida",
  dinner: "Cena",
  snack: "Snack",
};
const MEAL_ORDER: Record<string, number> = {
  breakfast: 0,
  lunch: 1,
  snack: 2,
  dinner: 3,
};

type ViewMode = "month" | "week" | "day";

// --- date helpers ----------------------------------------------------------
const planDay = (d: Date) => (d.getDay() + 6) % 7; // 0=Mon … 6=Sun
const addDays = (d: Date, n: number) => {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
};
const startOfWeek = (d: Date) => addDays(d, -planDay(d)); // Monday
const toISO = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")}`;
const sameDay = (a: Date, b: Date) => toISO(a) === toISO(b);

function sortItems(items: DietPlanItem[]): DietPlanItem[] {
  return [...items].sort((a, b) => {
    if (a.scheduled_time && b.scheduled_time)
      return a.scheduled_time.localeCompare(b.scheduled_time);
    if (a.scheduled_time) return -1;
    if (b.scheduled_time) return 1;
    const ma = a.meal_type ? MEAL_ORDER[a.meal_type] ?? 9 : 9;
    const mb = b.meal_type ? MEAL_ORDER[b.meal_type] ?? 9 : 9;
    return ma - mb;
  });
}

function StatusDot({ status }: { status: string }) {
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${
        status === "proposed" ? "bg-amber-400" : "bg-green-500"
      }`}
    />
  );
}

function ItemCard({
  item,
  onConfirm,
  onDelete,
}: {
  item: DietPlanItem;
  onConfirm: (i: DietPlanItem) => void;
  onDelete: (i: DietPlanItem) => void;
}) {
  const proposed = item.status === "proposed";
  return (
    <div
      className={`group flex items-start justify-between gap-3 rounded-xl border-2 bg-white p-4 transition-all duration-200 hover:shadow-md ${
        proposed ? "border-amber-200 hover:border-amber-300" : "border-emerald-200 hover:border-emerald-300"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          {item.meal_type && (
            <span className="badge-gray text-[11px]">
              {MEAL_ES[item.meal_type] ?? item.meal_type}
            </span>
          )}
          {item.scheduled_time && (
            <span className="text-xs text-gray-400 font-mono">🕐 {item.scheduled_time}</span>
          )}
          <span className={proposed ? "badge-amber" : "badge-green"}>
            <StatusDot status={item.status} />
            {proposed ? "Propuesta" : "Confirmada"}
          </span>
        </div>
        <p className="font-semibold text-gray-800">{item.title}</p>
        {item.description && (
          <p className="mt-1 text-sm text-gray-500 truncate">{item.description}</p>
        )}
        {item.calories != null && (
          <p className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-lg bg-gray-100 px-2 py-1 font-semibold text-gray-700">
              {Math.round(item.calories)} kcal
            </span>
            {item.protein_g != null && (
              <span className="rounded-lg bg-blue-50 px-2 py-1 font-semibold text-blue-700">
                P {Math.round(item.protein_g)}g
              </span>
            )}
            {item.carbs_g != null && (
              <span className="rounded-lg bg-amber-50 px-2 py-1 font-semibold text-amber-700">
                C {Math.round(item.carbs_g)}g
              </span>
            )}
            {item.fat_g != null && (
              <span className="rounded-lg bg-red-50 px-2 py-1 font-semibold text-red-700">
                G {Math.round(item.fat_g)}g
              </span>
            )}
            {item.fiber_g != null && (
              <span className="rounded-lg bg-lime-50 px-2 py-1 font-semibold text-lime-700">
                Fibra {Math.round(item.fiber_g)}g
              </span>
            )}
          </p>
        )}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1.5">
        {proposed && (
          <button
            onClick={() => onConfirm(item)}
            className="btn-primary text-xs px-3 py-1.5"
          >
            ✅ Confirmar
          </button>
        )}
        <button
          onClick={() => onDelete(item)}
          className="btn-danger text-xs opacity-0 group-hover:opacity-100 transition-opacity"
        >
          🗑️ Eliminar
        </button>
      </div>
    </div>
  );
}

export default function Diet() {
  const [items, setItems] = useState<DietPlanItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>("week");
  const [anchor, setAnchor] = useState(new Date());
  const today = new Date();

  const [form, setForm] = useState({
    title: "",
    scheduled_date: "",
    meal_type: "",
    scheduled_time: "",
    description: "",
  });

  useEffect(() => {
    api
      .get<DietPlanItem[]>("/me/diet-plan")
      .then((r) => setItems(r.data))
      .finally(() => setLoading(false));
  }, []);

  // Items grouped by ISO date, plus an "undated" bucket.
  const { byDate, undated } = useMemo(() => {
    const map = new Map<string, DietPlanItem[]>();
    const und: DietPlanItem[] = [];
    for (const it of items) {
      if (!it.scheduled_date) und.push(it);
      else {
        const arr = map.get(it.scheduled_date) ?? [];
        arr.push(it);
        map.set(it.scheduled_date, arr);
      }
    }
    return { byDate: map, undated: und };
  }, [items]);

  const itemsForDate = (d: Date): DietPlanItem[] =>
    sortItems(byDate.get(toISO(d)) ?? []);

  // Indicators for the header: scoped to the week the calendar is currently showing.
  const weekStats = useMemo(() => {
    const start = startOfWeek(anchor);
    const days = Array.from({ length: 7 }, (_, i) => addDays(start, i));
    let total = 0;
    let confirmed = 0;
    let kcal = 0;
    for (const d of days) {
      for (const it of itemsForDate(d)) {
        total++;
        if (it.status === "confirmed") confirmed++;
        if (it.calories != null) kcal += it.calories;
      }
    }
    return {
      total,
      confirmed,
      proposed: total - confirmed,
      kcal: Math.round(kcal),
      adherence: total ? Math.round((confirmed / total) * 100) : 0,
    };
  }, [anchor, byDate]);

  const confirm = async (item: DietPlanItem) => {
    const { data } = await api.patch<DietPlanItem>(`/me/diet-plan/${item.id}`, {
      status: "confirmed",
    });
    setItems((xs) => xs.map((x) => (x.id === item.id ? data : x)));
  };
  const remove = async (item: DietPlanItem) => {
    await api.delete(`/me/diet-plan/${item.id}`);
    setItems((xs) => xs.filter((x) => x.id !== item.id));
  };
  const add = async () => {
    if (!form.title.trim()) return;
    const payload = {
      title: form.title.trim(),
      scheduled_date: form.scheduled_date || undefined,
      meal_type: form.meal_type || undefined,
      scheduled_time: form.scheduled_time || undefined,
      description: form.description.trim() || undefined,
    };
    const { data } = await api.post<DietPlanItem>("/me/diet-plan", payload);
    setItems((xs) => [...xs, data]);
    setForm({ title: "", scheduled_date: "", meal_type: "", scheduled_time: "", description: "" });
  };

  const openDay = (d: Date) => {
    setAnchor(d);
    setView("day");
  };

  const step = (dir: number) => {
    if (view === "day") setAnchor((a) => addDays(a, dir));
    else if (view === "week") setAnchor((a) => addDays(a, dir * 7));
    else setAnchor((a) => new Date(a.getFullYear(), a.getMonth() + dir, 1));
  };

  const navLabel = () => {
    if (view === "day")
      return `${DAYS_FULL[planDay(anchor)]} ${anchor.getDate()} de ${MONTHS[anchor.getMonth()]}`;
    if (view === "week") {
      const s = startOfWeek(anchor);
      const e = addDays(s, 6);
      return `${s.getDate()} ${MONTHS[s.getMonth()].slice(0, 3)} – ${e.getDate()} ${MONTHS[e.getMonth()].slice(0, 3)}`;
    }
    return `${MONTHS[anchor.getMonth()]} ${anchor.getFullYear()}`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-green-600 to-emerald-500 bg-clip-text text-transparent">
            Dieta recomendada
          </h1>
          <p className="mt-0.5 text-sm text-gray-500">Planifica y confirma tus comidas</p>
        </div>
        <div className="flex overflow-hidden rounded-xl border-2 border-gray-100 bg-gray-50 p-0.5">
          {(["month", "week", "day"] as ViewMode[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-200 ${
                view === v
                  ? "bg-white text-green-700 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {v === "month" ? "📅 Mes" : v === "week" ? "📆 Semana" : "☀️ Día"}
            </button>
          ))}
        </div>
      </div>

      {/* Weekly indicators */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon="🍽️"
          label="Semana"
          value={`${weekStats.total} comida${weekStats.total === 1 ? "" : "s"}`}
          sub="planificadas"
          accent="#16a34a"
        />
        <StatCard
          icon="✅"
          label="Confirmadas"
          value={`${weekStats.confirmed} (${weekStats.adherence}%)`}
          sub="de la semana"
          accent="#16a34a"
        />
        <StatCard
          icon="⏳"
          label="Pendientes"
          value={`${weekStats.proposed}`}
          sub="por confirmar"
          accent="#f59e0b"
        />
        <StatCard
          icon="🔥"
          label="Kcal planificadas"
          value={weekStats.kcal > 0 ? `${weekStats.kcal.toLocaleString("es-ES")}` : "—"}
          sub="esta semana"
          accent="#16a34a"
        />
      </div>

      {/* Navigation bar */}
      <div className="flex items-center justify-between rounded-2xl bg-white/60 p-2 backdrop-blur-sm border border-white/50 shadow-sm">
        <div className="flex items-center gap-1">
          <button onClick={() => step(-1)} className="btn-ghost px-2.5 py-2 text-lg">←</button>
          <button onClick={() => setAnchor(new Date())} className="btn-ghost px-3 py-2 font-semibold">📍 Hoy</button>
          <button onClick={() => step(1)} className="btn-ghost px-2.5 py-2 text-lg">→</button>
          <span className="ml-2 text-sm font-bold text-gray-700">{navLabel()}</span>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5"><StatusDot status="confirmed" /> Confirmada</span>
          <span className="flex items-center gap-1.5"><StatusDot status="proposed" /> Propuesta</span>
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500">Cargando…</p>
      ) : (
        <>
          {view === "day" && (
            <DayView items={itemsForDate(anchor)} onConfirm={confirm} onDelete={remove} />
          )}
          {view === "week" && (
            <WeekView anchor={anchor} today={today} itemsForDate={itemsForDate} onOpenDay={openDay} />
          )}
          {view === "month" && (
            <MonthView anchor={anchor} today={today} itemsForDate={itemsForDate} onOpenDay={openDay} />
          )}
        </>
      )}

      {undated.length > 0 && (
        <section className="card">
          <div className="card-header">
            <span className="text-lg">📌</span>
            <h2 className="font-bold text-gray-800">Sin fecha asignada</h2>
          </div>
          <div className="space-y-2">
            {sortItems(undated).map((it) => (
              <ItemCard key={it.id} item={it} onConfirm={confirm} onDelete={remove} />
            ))}
          </div>
        </section>
      )}

      {/* Add food form */}
      <section className="card">
        <div className="card-header">
          <span className="text-lg">➕</span>
          <h2 className="font-bold text-gray-800">Añadir comida al plan</h2>
        </div>
        <div className="space-y-3">
          <input
            className="input-field w-full"
            placeholder="Título (ej. Avena con fruta y nueces)"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <div className="flex flex-wrap gap-2">
            <input
              type="date"
              className="input-field"
              value={form.scheduled_date}
              onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })}
            />
            <select
              className="input-field"
              value={form.meal_type}
              onChange={(e) => setForm({ ...form, meal_type: e.target.value })}
            >
              <option value="">🍽️ Tipo de comida</option>
              {Object.entries(MEAL_ES).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <input
              type="time"
              className="input-field"
              value={form.scheduled_time}
              onChange={(e) => setForm({ ...form, scheduled_time: e.target.value })}
            />
          </div>
          <input
            className="input-field w-full"
            placeholder="Descripción o ingredientes (opcional)"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <button
            onClick={add}
            className="btn-primary inline-flex items-center gap-2"
          >
            <span>➕</span> Añadir al plan
          </button>
        </div>
      </section>
    </div>
  );
}

function DayView({
  items,
  onConfirm,
  onDelete,
}: {
  items: DietPlanItem[];
  onConfirm: (i: DietPlanItem) => void;
  onDelete: (i: DietPlanItem) => void;
}) {
  if (items.length === 0)
    return (
      <div className="card py-10 text-center">
        <span className="text-4xl">🍽️</span>
        <p className="mt-3 text-gray-500 font-medium">No hay comidas para este día.</p>
        <p className="text-sm text-gray-400">Añade una nueva o pídele a NutriBot que te planifique.</p>
      </div>
    );
  return (
    <div className="space-y-3">
      {items.map((it) => (
        <ItemCard key={it.id} item={it} onConfirm={onConfirm} onDelete={onDelete} />
      ))}
    </div>
  );
}

function Chip({ item }: { item: DietPlanItem }) {
  return (
    <div
      className={`flex items-center gap-1.5 truncate rounded-lg px-2 py-1.5 text-xs font-medium transition-colors ${
        item.status === "proposed"
          ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
          : "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
      }`}
      title={item.title}
    >
      <StatusDot status={item.status} />
      {item.scheduled_time && <span className="text-[10px] opacity-60">{item.scheduled_time}</span>}
      <span className="truncate">{item.title}</span>
    </div>
  );
}

function WeekView({
  anchor,
  today,
  itemsForDate,
  onOpenDay,
}: {
  anchor: Date;
  today: Date;
  itemsForDate: (d: Date) => DietPlanItem[];
  onOpenDay: (d: Date) => void;
}) {
  const start = startOfWeek(anchor);
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i));
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
      {days.map((d, i) => {
        const dayItems = itemsForDate(d);
        const isToday = sameDay(d, today);
        return (
          <button
            key={i}
            onClick={() => onOpenDay(d)}
            className={`flex min-h-[130px] flex-col rounded-xl border-2 p-2.5 text-left transition-all duration-200 hover:shadow-md ${
              isToday
                ? "border-green-300 bg-green-50/80 ring-2 ring-green-200"
                : "border-gray-100 bg-white hover:border-gray-200"
            }`}
          >
            <div className="mb-2 flex items-baseline justify-between">
              <span className={`text-xs font-bold ${isToday ? "text-green-700" : "text-gray-500"}`}>
                {DAYS_SHORT[i]}
              </span>
              <span className={`text-lg font-bold ${isToday ? "text-green-600" : "text-gray-400"}`}>
                {d.getDate()}
              </span>
            </div>
            <div className="space-y-1 flex-1">
              {dayItems.length === 0 ? (
                <span className="text-[11px] text-gray-300">—</span>
              ) : (
                dayItems.map((it) => <Chip key={it.id} item={it} />)
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function MonthView({
  anchor,
  today,
  itemsForDate,
  onOpenDay,
}: {
  anchor: Date;
  today: Date;
  itemsForDate: (d: Date) => DietPlanItem[];
  onOpenDay: (d: Date) => void;
}) {
  const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  const gridStart = startOfWeek(first);
  const weeks = Array.from({ length: 6 }, (_, w) =>
    Array.from({ length: 7 }, (_, d) => addDays(gridStart, w * 7 + d)),
  );
  const month = anchor.getMonth();

  return (
    <div className="overflow-hidden rounded-2xl border-2 border-gray-100 bg-white shadow-sm">
      <div className="grid grid-cols-7 border-b-2 border-gray-100 bg-gray-50/80 text-center text-xs font-bold text-gray-500">
        {DAYS_SHORT.map((d) => (
          <div key={d} className="py-2">{d}</div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {weeks.flat().map((d, i) => {
          const inMonth = d.getMonth() === month;
          const dayItems = itemsForDate(d);
          const isToday = sameDay(d, today);
          const shown = dayItems.slice(0, 3);
          return (
            <button
              key={i}
              onClick={() => onOpenDay(d)}
              className={`min-h-[88px] border-b border-r border-gray-100 p-2 text-left align-top transition-all duration-150 hover:bg-green-50/50 ${
                inMonth ? "" : "bg-gray-50/80 text-gray-300"
              }`}
            >
              <div className="mb-1.5 text-right">
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                    isToday
                      ? "bg-green-600 text-white shadow-md shadow-green-300"
                      : inMonth
                      ? "text-gray-700"
                      : "text-gray-300"
                  }`}
                >
                  {d.getDate()}
                </span>
              </div>
              <div className="space-y-0.5">
                {shown.map((it) => (
                  <div
                    key={it.id}
                    className={`flex items-center gap-1 truncate rounded px-1 py-0.5 text-[10px] font-medium ${
                      it.status === "proposed" ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"
                    }`}
                    title={it.title}
                  >
                    <StatusDot status={it.status} />
                    <span className="truncate">{it.title}</span>
                  </div>
                ))}
                {dayItems.length > shown.length && (
                  <div className="text-[10px] text-gray-400 pl-1">+{dayItems.length - shown.length} más</div>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
