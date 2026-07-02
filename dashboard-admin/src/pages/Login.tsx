import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
      navigate("/");
    } catch {
      setError("Credenciales inválidas.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-purple-100 px-4">
      <div className="w-full max-w-sm rounded-3xl bg-white/80 backdrop-blur-xl border border-white/50 p-8 shadow-2xl shadow-indigo-900/10">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-xl shadow-indigo-500/30">
            <span className="text-3xl">🛠️</span>
          </div>
          <h1 className="text-2xl font-extrabold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            NutriBot Admin
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Accede con tu cuenta de administrador
          </p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            placeholder="Email"
            className="input-field w-full"
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="Contraseña"
            className="input-field w-full"
          />
          {error && (
            <div className="rounded-xl border-2 border-red-200 bg-red-50 p-3 text-sm text-red-600 text-center">
              ⚠️ {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || !email || !password}
            className="btn-primary w-full py-3 text-base"
          >
            {loading ? "⏳ Entrando…" : "🔐 Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
