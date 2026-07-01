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
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 shadow">
        <h1 className="mb-1 text-2xl font-bold">🥗 NutriBot</h1>
        <p className="mb-6 text-sm text-gray-500">
          Escribe <span className="font-mono font-semibold">/login</span> a tu bot de
          Telegram y pega aquí el código que te dé.
        </p>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            inputMode="numeric"
            placeholder="Código de 6 dígitos"
            className="w-full rounded-lg border border-gray-300 px-4 py-2 text-center text-lg tracking-widest focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading || code.length < 4}
            className="w-full rounded-lg bg-brand py-2 font-medium text-white transition hover:bg-brand-dark disabled:opacity-50"
          >
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
