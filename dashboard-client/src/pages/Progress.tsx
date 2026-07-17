import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { StatCard } from "../components/StatCard";
import { DailySummary, HistoryPoint, WeightPoint } from "../types";

const TOOLTIP_STYLE = {
  borderRadius: "12px",
  border: "1px solid rgba(0,0,0,0.06)",
  boxShadow: "0 10px 40px rgba(0,0,0,0.1)",
  fontSize: "13px",
};

function average(points: HistoryPoint[], key: keyof HistoryPoint): number {
  if (points.length === 0) return 0;
  const sum = points.reduce((s, p) => s + (p[key] as number), 0);
  return sum / points.length;
}

function findWeightNDaysAgo(points: WeightPoint[], days: number): WeightPoint | null {
  if (points.length === 0) return null;
  const latest = new Date(points[points.length - 1].logged_at);
  const target = new Date(latest);
  target.setDate(target.getDate() - days);
  let best: WeightPoint | null = null;
  for (const w of points) {
    if (new Date(w.logged_at) <= target) best = w;
  }
  return best;
}

const WATER_QUICK_ADD = [
  { label: "🥛 Vaso", ml: 200 },
  { label: "🍶 Botella", ml: 500 },
  { label: "🚰 1 L", ml: 1000 },
];

function shortDate(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

function MacroBar({
  label,
  value,
  target,
  unit,
  color,
}: {
  label: string;
  value: number;
  target: number | null;
  unit: string;
  color: string;
}) {
  const pct = target ? Math.min((value / target) * 100, 100) : 0;
  return (
    <div>
      <div className="mb-1.5 flex justify-between text-sm">
        <span className="font-semibold text-gray-700">{label}</span>
        <span className="text-gray-500">
          <span className="font-bold text-gray-800">{Math.round(value)}</span>
          {target ? <span className="text-gray-400"> / {Math.round(target)}</span> : ""} <span className="text-xs">{unit}</span>
        </span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-gray-100 shadow-inner">
        <div
          className="h-3 rounded-full transition-all duration-500 ease-out shadow-sm"
          style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function Progress() {
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [history, setHistory] = useState<Array<HistoryPoint & { label: string }>>([]);
  const [weight, setWeight] = useState<WeightPoint[]>([]);
  const [loggingWater, setLoggingWater] = useState(false);

  const loadSummary = () =>
    api.get<DailySummary>("/me/nutrition/summary").then((r) => setSummary(r.data));

  useEffect(() => {
    loadSummary();
    api
      .get<HistoryPoint[]>("/me/nutrition/history", { params: { days: 14 } })
      .then((r) =>
        setHistory(r.data.map((p) => ({ ...p, label: shortDate(p.date) }))),
      );
    api.get<WeightPoint[]>("/me/weight").then((r) => setWeight(r.data));
  }, []);

  const addWater = async (ml: number) => {
    setLoggingWater(true);
    try {
      await api.post("/me/water", { amount_ml: ml });
      await loadSummary();
    } finally {
      setLoggingWater(false);
    }
  };

  const t = summary?.targets;

  const weightData = weight.map((w) => ({
    label: shortDate(w.logged_at.slice(0, 10)),
    weight: w.weight_kg,
  }));

  // --- KPI strip: derived from the 14-day history + weight log, no extra requests.
  const kpis = useMemo(() => {
    let streak = 0;
    for (let i = history.length - 1; i >= 0; i--) {
      if (history[i].calories > 0) streak++;
      else break;
    }
    const last7 = history.slice(-7);
    const prev7 = history.slice(-14, -7);
    const avgCal7 = average(last7, "calories");
    const avgCalPrev7 = average(prev7, "calories");
    const calDeltaPct =
      prev7.length > 0 && avgCalPrev7 > 0
        ? ((avgCal7 - avgCalPrev7) / avgCalPrev7) * 100
        : null;
    const avgWater7 = average(last7, "water_ml");

    const latestWeight = weight[weight.length - 1] ?? null;
    const weekAgoWeight = findWeightNDaysAgo(weight, 7);
    const weightDelta =
      latestWeight && weekAgoWeight
        ? latestWeight.weight_kg - weekAgoWeight.weight_kg
        : null;

    return { streak, avgCal7, calDeltaPct, avgWater7, latestWeight, weightDelta };
  }, [history, weight]);

  // --- Today's macro-calorie split (protein/carbs/fat), for the donut chart.
  const macroSplit = useMemo(() => {
    if (!summary) return [];
    const raw = [
      { name: "Proteína", kcal: summary.totals.protein_g * 4, color: "#2563eb" },
      { name: "Carbohidratos", kcal: summary.totals.carbs_g * 4, color: "#f59e0b" },
      { name: "Grasas", kcal: summary.totals.fat_g * 9, color: "#ef4444" },
    ];
    return raw.filter((d) => d.kcal > 0).map((d) => ({ ...d, kcal: Math.round(d.kcal) }));
  }, [summary]);
  const macroSplitTotal = macroSplit.reduce((s, d) => s + d.kcal, 0);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold bg-gradient-to-r from-green-600 to-emerald-500 bg-clip-text text-transparent">
          Tu progreso
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Seguimiento diario de tu nutrición y evolución
        </p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon="🔥"
          label="Racha"
          value={`${kpis.streak} día${kpis.streak === 1 ? "" : "s"}`}
          sub="registrando comidas"
          accent="#16a34a"
        />
        <StatCard
          icon="⚡"
          label="Calorías (7d)"
          value={history.length ? `${Math.round(kpis.avgCal7)} kcal` : "—"}
          sub={
            kpis.calDeltaPct != null
              ? `${kpis.calDeltaPct >= 0 ? "▲" : "▼"} ${Math.abs(kpis.calDeltaPct).toFixed(0)}% vs. semana anterior`
              : "Promedio diario"
          }
          accent="#16a34a"
        />
        <StatCard
          icon="⚖️"
          label="Peso actual"
          value={kpis.latestWeight ? `${kpis.latestWeight.weight_kg} kg` : "—"}
          sub={
            kpis.weightDelta != null
              ? `${kpis.weightDelta >= 0 ? "+" : ""}${kpis.weightDelta.toFixed(1)} kg (7d)`
              : "Sin registros recientes"
          }
          accent="#2563eb"
        />
        <StatCard
          icon="💧"
          label="Agua (7d)"
          value={history.length ? `${(kpis.avgWater7 / 1000).toFixed(1)} L` : "—"}
          sub={
            summary?.water_target_ml
              ? `Objetivo ${(summary.water_target_ml / 1000).toFixed(1)} L`
              : "Promedio diario"
          }
          accent="#0ea5e9"
        />
      </div>

      {/* Today's macros + distribution */}
      <section className="grid gap-6 md:grid-cols-5">
        <div className="card md:col-span-3">
          <div className="card-header">
            <span className="text-xl">📅</span>
            <h2 className="font-bold text-gray-800">Resumen de hoy</h2>
          </div>
          {summary ? (
            <div className="space-y-5">
              <MacroBar label="🔥 Calorías" value={summary.totals.calories} target={t?.calories ?? null} unit="kcal" color="#16a34a" />
              <MacroBar label="💪 Proteína" value={summary.totals.protein_g} target={t?.protein_g ?? null} unit="g" color="#2563eb" />
              <MacroBar label="🍚 Carbohidratos" value={summary.totals.carbs_g} target={t?.carbs_g ?? null} unit="g" color="#f59e0b" />
              <MacroBar label="🧈 Grasas" value={summary.totals.fat_g} target={t?.fat_g ?? null} unit="g" color="#ef4444" />
              <MacroBar label="🌾 Fibra" value={summary.totals.fiber_g} target={t?.fiber_g ?? null} unit="g" color="#84cc16" />
            </div>
          ) : (
            <div className="flex items-center gap-3 py-6 text-gray-400">
              <span className="animate-spin text-xl">⏳</span>
              <span>Cargando resumen…</span>
            </div>
          )}
        </div>

        <div className="card md:col-span-2">
          <div className="card-header">
            <span className="text-xl">🍽️</span>
            <h2 className="font-bold text-gray-800">Reparto de macros</h2>
          </div>
          {macroSplit.length > 0 ? (
            <div className="relative">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={macroSplit}
                    dataKey="kcal"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={3}
                    stroke="none"
                  >
                    {macroSplit.map((d) => (
                      <Cell key={d.name} fill={d.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(value: number, name: string) => [`${value} kcal`, name]}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={32}
                    iconType="circle"
                    iconSize={8}
                    formatter={(value) => <span className="text-xs text-gray-600">{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute left-1/2 top-[42%] -translate-x-1/2 -translate-y-1/2 text-center">
                <p className="text-xl font-extrabold text-gray-800">{macroSplitTotal}</p>
                <p className="text-[10px] font-semibold text-gray-400">kcal</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-16 text-center text-gray-400">
              <p>Aún no hay comidas registradas hoy.</p>
            </div>
          )}
        </div>
      </section>

      {/* Hydration */}
      <section className="card">
        <div className="card-header">
          <span className="text-xl">💧</span>
          <h2 className="font-bold text-gray-800">Hidratación</h2>
        </div>
        {summary ? (
          <div className="space-y-4">
            <MacroBar
              label="💧 Agua"
              value={summary.water_ml}
              target={summary.water_target_ml}
              unit="ml"
              color="#0ea5e9"
            />
            <div className="flex flex-wrap gap-2">
              {WATER_QUICK_ADD.map((q) => (
                <button
                  key={q.ml}
                  onClick={() => addWater(q.ml)}
                  disabled={loggingWater}
                  className="btn-ghost rounded-xl border-2 border-sky-100 px-3 py-2 text-sm font-semibold text-sky-700 hover:border-sky-200 hover:bg-sky-50 disabled:opacity-50"
                >
                  {q.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 py-6 text-gray-400">
            <span className="animate-spin text-xl">⏳</span>
            <span>Cargando…</span>
          </div>
        )}
      </section>

      {/* Water history chart */}
      <section className="card">
        <div className="card-header">
          <span className="text-xl">📈</span>
          <h2 className="font-bold text-gray-800">Hidratación — últimos 14 días</h2>
        </div>
        {history.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={history} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
              <XAxis dataKey="label" fontSize={12} tick={{ fill: "#9ca3af" }} />
              <YAxis fontSize={12} tick={{ fill: "#9ca3af" }} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value: number) => [`${value} ml`, "Agua"]}
              />
              {summary?.water_target_ml ? (
                <ReferenceLine y={summary.water_target_ml} stroke="#0ea5e9" strokeDasharray="4 4" />
              ) : null}
              <defs>
                <linearGradient id="waterGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="water_ml"
                stroke="#0ea5e9"
                strokeWidth={2.5}
                fill="url(#waterGradient)"
                dot={{ fill: "#0ea5e9", r: 3, strokeWidth: 0 }}
                activeDot={{ r: 5, fill: "#0ea5e9", stroke: "#fff", strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="py-8 text-center text-gray-400">Sin datos aún.</p>
        )}
      </section>

      {/* Calories chart */}
      <section className="card">
        <div className="card-header">
          <span className="text-xl">📊</span>
          <h2 className="font-bold text-gray-800">Calorías — últimos 14 días</h2>
        </div>
        {history.length > 0 ? (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={history} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
              <XAxis dataKey="label" fontSize={12} tick={{ fill: "#9ca3af" }} />
              <YAxis fontSize={12} tick={{ fill: "#9ca3af" }} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value: number) => [`${Math.round(value)} kcal`, "Calorías"]}
              />
              {t?.calories ? (
                <ReferenceLine y={t.calories} stroke="#16a34a" strokeDasharray="4 4" />
              ) : null}
              <Bar dataKey="calories" fill="url(#calorieGradient)" radius={[6, 6, 0, 0]} />
              <defs>
                <linearGradient id="calorieGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#16a34a" />
                  <stop offset="100%" stopColor="#86efac" />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="py-8 text-center text-gray-400">Sin datos aún. ¡Empieza a registrar comidas!</p>
        )}
      </section>

      {/* Weight chart */}
      <section className="card">
        <div className="card-header">
          <span className="text-xl">⚖️</span>
          <h2 className="font-bold text-gray-800">Evolución de peso</h2>
        </div>
        {weightData.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={weightData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" fontSize={12} tick={{ fill: "#9ca3af" }} />
              <YAxis domain={["dataMin - 1", "dataMax + 1"]} fontSize={12} tick={{ fill: "#9ca3af" }} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value: number) => [`${value} kg`, "Peso"]}
              />
              <Line
                type="monotone"
                dataKey="weight"
                stroke="#2563eb"
                strokeWidth={3}
                dot={{ fill: "#2563eb", r: 4, strokeWidth: 0 }}
                activeDot={{ r: 6, fill: "#2563eb", stroke: "#fff", strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="py-8 text-center text-gray-400">Aún no hay registros de peso.</p>
        )}
      </section>
    </div>
  );
}
