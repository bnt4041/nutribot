export function StatCard({
  icon,
  label,
  value,
  sub,
  accent = "#16a34a",
}: {
  icon: string;
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="card !p-4 flex items-center gap-3">
      <div
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-xl"
        style={{ backgroundColor: `${accent}1a` }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-bold uppercase tracking-wide text-gray-400">
          {label}
        </p>
        <p className="text-lg font-extrabold leading-tight text-gray-800 truncate">
          {value}
        </p>
        {sub && <p className="mt-0.5 text-xs text-gray-400 truncate">{sub}</p>}
      </div>
    </div>
  );
}
