import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { UsageMetrics } from "../types";

function Card({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="card group">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-2xl">{icon}</span>
        <span className="text-sm font-medium text-gray-500">{label}</span>
      </div>
      <div className="text-3xl font-extrabold text-gray-900">{value}</div>
    </div>
  );
}

export default function Metrics() {
  const [data, setData] = useState<UsageMetrics | null>(null);

  useEffect(() => {
    api
      .get<UsageMetrics>("/admin/metrics/usage", { params: { days: 30 } })
      .then((r) => setData(r.data));
  }, []);

  if (!data) return <p className="text-gray-500">Cargando…</p>;

  const chart = data.series.map((p) => ({
    label: p.date.slice(5),
    tokens: p.tokens_prompt + p.tokens_completion,
    cost: p.cost_usd,
  }));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
          Métricas
        </h1>
        <p className="mt-1 text-sm text-gray-500">Últimos {data.days} días de actividad</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card label="Tokens totales" value={data.tokens_total.toLocaleString()} icon="🪙" />
        <Card label="Prompt / Completion" value={`${data.tokens_prompt.toLocaleString()} / ${data.tokens_completion.toLocaleString()}`} icon="📥📤" />
        <Card label="Coste estimado" value={`$${data.estimated_cost_usd.toFixed(4)}`} icon="💰" />
        <Card label="Respuestas IA" value={data.assistant_messages.toLocaleString()} icon="🤖" />
      </div>

      {/* Chart */}
      <section className="card">
        <div className="card-header">
          <span className="text-xl">📊</span>
          <h2 className="font-bold text-gray-800">Tokens por día</h2>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chart} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
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
            <Bar dataKey="tokens" fill="url(#tokenGradient)" radius={[6, 6, 0, 0]} />
            <defs>
              <linearGradient id="tokenGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4f46e5" />
                <stop offset="100%" stopColor="#a78bfa" />
              </linearGradient>
            </defs>
          </BarChart>
        </ResponsiveContainer>
        <p className="mt-3 text-xs text-gray-400">
          Precios: ${data.prices_per_mtok.input}/M entrada · $
          {data.prices_per_mtok.output}/M salida (configurable).
        </p>
      </section>
    </div>
  );
}
