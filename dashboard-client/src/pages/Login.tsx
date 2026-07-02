import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(code.trim());
      navigate("/");
    } catch {
      setError("Código inválido o caducado. Pide uno nuevo con /login en el bot.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-green-50 via-white to-emerald-100 px-4">
      <div className="w-full max-w-sm rounded-3xl bg-white/80 backdrop-blur-xl border border-white/50 p-8 shadow-2xl shadow-green-900/10">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 shadow-xl shadow-green-500/30">
            <span className="text-3xl">🥗</span>
          </div>
          <h1 className="text-2xl font-extrabold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
            NutriBot
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Escribe <span className="rounded-lg bg-green-100 px-2 py-0.5 font-mono font-semibold text-green-700">/login</span> a tu bot de
            Telegram y pega aquí el código que te dé.
          </p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            inputMode="numeric"
            placeholder="Código de 6 dígitos"
            className="input-field w-full text-center text-2xl font-mono tracking-[0.3em]"
          />
          {error && (
            <div className="rounded-xl border-2 border-red-200 bg-red-50 p-3 text-sm text-red-600 text-center">
              ⚠️ {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || code.length < 4}
            className="btn-primary w-full py-3 text-base"
          >
            {loading ? "⏳ Entrando…" : "🔐 Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
