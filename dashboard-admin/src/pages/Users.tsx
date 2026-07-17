import { useEffect, useState } from "react";
import { api } from "../api/client";
import { AdminUser, AppSettings } from "../types";

function daysSince(iso: string): number {
  return (Date.now() - new Date(iso).getTime()) / 86_400_000;
}

// Falls back to account creation when the user has never sent a message,
// matching the cron's own inactivity reference (scripts/send_reminders.py).
function lastActivity(u: AdminUser): { iso: string; everChatted: boolean } {
  return u.last_message_at
    ? { iso: u.last_message_at, everChatted: true }
    : { iso: u.created_at, everChatted: false };
}

function formatLastMessage(u: AdminUser, thresholdDays: number) {
  const { iso, everChatted } = lastActivity(u);
  const days = daysSince(iso);
  const label = everChatted
    ? days < 1
      ? "hoy"
      : `hace ${Math.floor(days)} d`
    : "nunca ha chateado";
  if (days >= thresholdDays) {
    return <span className="badge-red">⚠️ {label}</span>;
  }
  return <span className="text-gray-600">{label}</span>;
}

export default function Users() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [savingSettings, setSavingSettings] = useState(false);

  const load = () => api.get<AdminUser[]>("/admin/users").then((r) => setUsers(r.data));
  const loadSettings = () =>
    api.get<AppSettings>("/admin/settings").then((r) => setSettings(r.data));

  useEffect(() => {
    load();
    loadSettings();
  }, []);

  const saveSettings = async (patch: Partial<AppSettings>) => {
    setSavingSettings(true);
    try {
      const { data } = await api.patch<AppSettings>("/admin/settings", patch);
      setSettings(data);
    } finally {
      setSavingSettings(false);
    }
  };

  const thresholdDays = settings?.inactivity_reminder_days ?? 3;
  const inactiveCount = users.filter(
    (u) => u.role === "client" && u.onboarding_completed_at && daysSince(lastActivity(u).iso) >= thresholdDays,
  ).length;

  const toggleActive = async (u: AdminUser) => {
    await api.patch(`/admin/users/${u.id}`, { is_active: !u.is_active });
    load();
  };

  const toggleRole = async (u: AdminUser) => {
    const role = u.role === "admin" ? "client" : "admin";
    await api.patch(`/admin/users/${u.id}`, { role });
    load();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Usuarios
          </h1>
          <p className="mt-0.5 text-sm text-gray-500">{users.length} registrados</p>
        </div>
        <button onClick={load} className="btn-secondary">🔄 Actualizar</button>
      </div>

      {/* Inactivity nudge settings */}
      <div className="rounded-2xl border-2 border-gray-100 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-bold text-gray-800">🔔 Recordatorio de inactividad</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {inactiveCount > 0
                ? `⚠️ ${inactiveCount} usuario(s) llevan ${thresholdDays}+ días sin chatear`
                : `Ningún usuario lleva ${thresholdDays}+ días sin chatear`}
              . Se avisa 3 veces cada {thresholdDays} días y luego un mensaje de despedida.
            </p>
          </div>
          {settings && (
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-gray-600">
                Cada
                <input
                  type="number"
                  min={1}
                  max={90}
                  className="input-field w-16 text-center"
                  value={settings.inactivity_reminder_days}
                  onChange={(e) => setSettings({ ...settings, inactivity_reminder_days: Number(e.target.value) })}
                  onBlur={(e) => saveSettings({ inactivity_reminder_days: Number(e.target.value) })}
                />
                días
              </label>
              <label className="flex items-center gap-2 text-sm">
                <span className="text-gray-500">Activado</span>
                <input
                  type="checkbox"
                  disabled={savingSettings}
                  checked={settings.inactivity_reminder_enabled}
                  onChange={(e) => saveSettings({ inactivity_reminder_enabled: e.target.checked })}
                />
              </label>
            </div>
          )}
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border-2 border-gray-100 bg-white shadow-sm">
        <table className="admin-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Telegram / Email</th>
              <th>Rol</th>
              <th>Onboarding</th>
              <th>Estado</th>
              <th>Última conversación</th>
              <th>Tokens</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td className="font-mono text-xs text-gray-400">#{u.id}</td>
                <td className="font-semibold">{u.full_name || "—"}</td>
                <td className="text-gray-500 text-xs">
                  {u.email || u.telegram_id || "—"}
                </td>
                <td>
                  <span className={u.role === "admin" ? "badge-indigo" : "badge-gray"}>
                    {u.role}
                  </span>
                </td>
                <td>
                  {u.onboarding_completed_at ? (
                    <span className="badge-green">✅ Completado</span>
                  ) : (
                    <span className="badge-gray">—</span>
                  )}
                </td>
                <td>
                  {u.is_active ? (
                    <span className="badge-green">🟢 Activo</span>
                  ) : (
                    <span className="badge-red">🔴 Inactivo</span>
                  )}
                </td>
                <td className="text-xs">
                  {u.role === "client" ? formatLastMessage(u, thresholdDays) : <span className="text-gray-300">—</span>}
                </td>
                <td className="text-xs text-gray-600">
                  {u.tokens_total > 0 ? (
                    <span title={`≈ $${u.estimated_cost_usd.toFixed(4)}`}>
                      {u.tokens_total.toLocaleString("es-ES")}
                    </span>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td>
                  <div className="flex gap-2">
                    <button
                      onClick={() => toggleActive(u)}
                      className="btn-ghost text-xs"
                    >
                      {u.is_active ? "⏸️ Desactivar" : "▶️ Activar"}
                    </button>
                    <button
                      onClick={() => toggleRole(u)}
                      className="btn-ghost text-xs"
                    >
                      {u.role === "admin" ? "👤 Hacer cliente" : "🛡️ Hacer admin"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
