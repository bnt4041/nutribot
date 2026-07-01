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
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Usuarios ({users.length})</h1>
      <div className="overflow-x-auto rounded-xl bg-white shadow">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Telegram / Email</th>
              <th className="px-4 py-3">Rol</th>
              <th className="px-4 py-3">Onboarding</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b last:border-0">
                <td className="px-4 py-3">{u.id}</td>
                <td className="px-4 py-3">{u.full_name || "—"}</td>
                <td className="px-4 py-3 text-gray-500">
                  {u.email || u.telegram_id || "—"}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      u.role === "admin"
                        ? "bg-indigo-100 text-indigo-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {u.onboarding_completed_at ? "✅" : "—"}
                </td>
                <td className="px-4 py-3">
                  {u.is_active ? (
                    <span className="text-green-600">activo</span>
                  ) : (
                    <span className="text-red-600">inactivo</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      onClick={() => toggleActive(u)}
                      className="rounded border px-2 py-1 text-xs hover:bg-gray-50"
                    >
                      {u.is_active ? "Desactivar" : "Activar"}
                    </button>
                    <button
                      onClick={() => toggleRole(u)}
                      className="rounded border px-2 py-1 text-xs hover:bg-gray-50"
                    >
                      {u.role === "admin" ? "Hacer cliente" : "Hacer admin"}
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
