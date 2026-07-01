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
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-gray-500">
          {Math.round(value)}
          {target ? ` / ${Math.round(target)}` : ""} {unit}
        </span>
      </div>
      <div className="h-2.5 w-full rounded-full bg-gray-100">
        <div
          className="h-2.5 rounded-full"
          style={{ width: `${pct}%`, backgroundColor: color }}
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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tu progreso</h1>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-4 font-semibold">Hoy</h2>
        {summary ? (
          <div className="space-y-4">
            <MacroBar label="Calorías" value={summary.totals.calories} target={t?.calories ?? null} unit="kcal" color="#16a34a" />
            <MacroBar label="Proteína" value={summary.totals.protein_g} target={t?.protein_g ?? null} unit="g" color="#2563eb" />
            <MacroBar label="Carbohidratos" value={summary.totals.carbs_g} target={t?.carbs_g ?? null} unit="g" color="#f59e0b" />
            <MacroBar label="Grasas" value={summary.totals.fat_g} target={t?.fat_g ?? null} unit="g" color="#ef4444" />
          </div>
        ) : (
          <p className="text-gray-500">Cargando…</p>
        )}
      </section>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-4 font-semibold">Calorías (últimos 14 días)</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={history} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" fontSize={12} />
            <YAxis fontSize={12} />
            <Tooltip />
            {t?.calories ? (
              <ReferenceLine y={t.calories} stroke="#16a34a" strokeDasharray="4 4" />
            ) : null}
            <Bar dataKey="calories" fill="#16a34a" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </section>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-4 font-semibold">Peso</h2>
        {weightData.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={weightData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" fontSize={12} />
              <YAxis domain={["dataMin - 1", "dataMax + 1"]} fontSize={12} />
              <Tooltip />
              <Line type="monotone" dataKey="weight" stroke="#2563eb" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-500">Aún no hay registros de peso.</p>
        )}
      </section>
    </div>
  );
}
