import { useEffect, useState } from "react";
import { api } from "../api/client";
import { AdminUser } from "../types";

export default function Users() {
  const [users, setUsers] = useState<AdminUser[]>([]);

  const load = () => api.get<AdminUser[]>("/admin/users").then((r) => setUsers(r.data));

  useEffect(() => {
    load();
  }, []);

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
