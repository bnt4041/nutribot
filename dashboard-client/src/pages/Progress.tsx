import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { DailySummary, HistoryPoint, WeightPoint } from "../types";

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

  useEffect(() => {
    api.get<DailySummary>("/me/nutrition/summary").then((r) => setSummary(r.data));
    api
      .get<HistoryPoint[]>("/me/nutrition/history", { params: { days: 14 } })
      .then((r) =>
        setHistory(r.data.map((p) => ({ ...p, label: shortDate(p.date) }))),
      );
    api.get<WeightPoint[]>("/me/weight").then((r) => setWeight(r.data));
  }, []);

  const t = summary?.targets;

  const weightData = weight.map((w) => ({
    label: shortDate(w.logged_at.slice(0, 10)),
    weight: w.weight_kg,
  }));

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

      {/* Today's macros */}
      <section className="card">
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
          </div>
        ) : (
          <div className="flex items-center gap-3 py-6 text-gray-400">
            <span className="animate-spin text-xl">⏳</span>
            <span>Cargando resumen…</span>
          </div>
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
                contentStyle={{
                  borderRadius: "12px",
                  border: "none",
                  boxShadow: "0 10px 40px rgba(0,0,0,0.1)",
                }}
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
                contentStyle={{
                  borderRadius: "12px",
                  border: "none",
                  boxShadow: "0 10px 40px rgba(0,0,0,0.1)",
                }}
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
