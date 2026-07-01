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

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white p-5 shadow">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Métricas (últimos {data.days} días)</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card label="Tokens totales" value={data.tokens_total.toLocaleString()} />
        <Card label="Prompt / Completion" value={`${data.tokens_prompt.toLocaleString()} / ${data.tokens_completion.toLocaleString()}`} />
        <Card label="Coste estimado" value={`$${data.estimated_cost_usd.toFixed(4)}`} />
        <Card label="Respuestas IA" value={data.assistant_messages.toLocaleString()} />
      </div>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-4 font-semibold">Tokens por día</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chart} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" fontSize={12} />
            <YAxis fontSize={12} />
            <Tooltip />
            <Bar dataKey="tokens" fill="#4f46e5" radius={[4, 4, 0, 0]} />
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
