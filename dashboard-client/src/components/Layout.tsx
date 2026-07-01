import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const links = [
  { to: "/", label: "Progreso", end: true },
  { to: "/perfil", label: "Perfil" },
  { to: "/conversaciones", label: "Conversaciones" },
];

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen">
      <header className="bg-brand text-white shadow">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <span className="text-lg font-semibold">🥗 NutriBot</span>
          <nav className="flex items-center gap-1">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  `rounded px-3 py-1.5 text-sm font-medium transition ${
                    isActive ? "bg-white/20" : "hover:bg-white/10"
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
            <button
              onClick={onLogout}
              className="ml-2 rounded px-3 py-1.5 text-sm font-medium hover:bg-white/10"
            >
              Salir
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
