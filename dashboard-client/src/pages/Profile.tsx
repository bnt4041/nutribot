import { ReactNode, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Note, Profile as ProfileType } from "../types";

const GOAL_ES: Record<string, string> = {
  lose: "Perder grasa",
  maintain: "Mantener peso",
  gain: "Ganar músculo",
};
const ACTIVITY_ES: Record<string, string> = {
  sedentary: "Sedentaria",
  light: "Ligera",
  moderate: "Moderada",
  active: "Alta",
  very_active: "Muy alta",
};
const SEX_ES: Record<string, string> = { male: "Hombre", female: "Mujer" };

const NOTE_CATEGORY_ES: Record<string, string> = {
  dislike: "No le gusta / evita",
  like: "Le gusta",
  medical: "Salud",
  habit: "Hábito",
  other: "Otro",
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-gray-50 py-3 text-sm last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className="font-semibold text-gray-800">{value}</span>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="flex items-center justify-between gap-4 py-3 text-sm">
      <span className="font-medium text-gray-600">{label}</span>
      {children}
    </label>
  );
}

type FormState = Record<string, string>;

function toForm(p: ProfileType): FormState {
  return {
    full_name: p.full_name ?? "",
    sex: p.sex ?? "",
    birth_date: p.birth_date ?? "",
    height_cm: p.height_cm?.toString() ?? "",
    current_weight_kg: p.current_weight_kg?.toString() ?? "",
    activity_level: p.activity_level ?? "",
    goal: p.goal ?? "",
    target_weight_kg: p.target_weight_kg?.toString() ?? "",
    weekly_rate_kg: p.weekly_rate_kg?.toString() ?? "",
    timezone: p.timezone ?? "",
    dietary_restrictions: p.dietary_restrictions.join(", "),
    allergies: p.allergies.join(", "),
  };
}

export default function Profile() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const [profile, setProfile] = useState<ProfileType | null>(null);
  const [error, setError] = useState(false);

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<FormState>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [notes, setNotes] = useState<Note[]>([]);
  const [newNote, setNewNote] = useState("");
  const [newCategory, setNewCategory] = useState("dislike");

  useEffect(() => {
    api
      .get<ProfileType>("/me")
      .then((r) => setProfile(r.data))
      .catch(() => setError(true));
    api.get<Note[]>("/me/notes").then((r) => setNotes(r.data)).catch(() => {});
  }, []);

  if (error) return <p className="text-red-600">No se pudo cargar el perfil.</p>;
  if (!profile) return <p className="text-gray-500">Cargando…</p>;

  const p = profile;
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const startEdit = () => {
    setForm(toForm(p));
    setSaveError(null);
    setEditing(true);
  };

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    const num = (v: string) => (v.trim() === "" ? undefined : Number(v));
    const str = (v: string) => (v.trim() === "" ? undefined : v.trim());
    const list = (v: string) =>
      v.split(",").map((x) => x.trim()).filter(Boolean);
    const payload = {
      full_name: str(form.full_name),
      sex: str(form.sex),
      birth_date: str(form.birth_date),
      height_cm: num(form.height_cm),
      current_weight_kg: num(form.current_weight_kg),
      activity_level: str(form.activity_level),
      goal: str(form.goal),
      target_weight_kg: num(form.target_weight_kg),
      weekly_rate_kg: num(form.weekly_rate_kg),
      timezone: str(form.timezone),
      dietary_restrictions: list(form.dietary_restrictions),
      allergies: list(form.allergies),
    };
    try {
      const { data } = await api.patch<ProfileType>("/me", payload);
      setProfile(data);
      setEditing(false);
    } catch (e: any) {
      setSaveError(e?.response?.data?.detail ?? "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  };

  const addNote = async () => {
    const content = newNote.trim();
    if (!content) return;
    const { data } = await api.post<Note>("/me/notes", {
      content,
      category: newCategory,
    });
    setNotes((n) => [...n, data]);
    setNewNote("");
  };

  const deleteNote = async (id: number) => {
    await api.delete(`/me/notes/${id}`);
    setNotes((n) => n.filter((x) => x.id !== id));
  };

  const deleteAccount = async () => {
    if (
      !window.confirm(
        "¿Seguro que quieres eliminar tu perfil? Se borrarán todos tus datos de forma permanente.",
      )
    )
      return;
    await api.delete("/me");
    logout();
    navigate("/login");
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-green-600 to-emerald-500 bg-clip-text text-transparent">
            Tu perfil
          </h1>
          <p className="mt-0.5 text-sm text-gray-500">Gestiona tus datos y objetivos</p>
        </div>
        {editing ? (
          <div className="flex gap-2">
            <button onClick={() => setEditing(false)} className="btn-secondary">Cancelar</button>
            <button onClick={save} disabled={saving} className="btn-primary">
              {saving ? "⏳ Guardando…" : "💾 Guardar"}
            </button>
          </div>
        ) : (
          <button onClick={startEdit} className="btn-primary">✏️ Editar</button>
        )}
      </div>

      {saveError && (
        <div className="rounded-xl border-2 border-red-200 bg-red-50 p-3 text-sm font-medium text-red-600">
          ⚠️ {saveError}
        </div>
      )}

      {editing ? (
        <section className="card">
          <div className="card-header">
            <span className="text-lg">📝</span>
            <h2 className="font-bold text-gray-800">Datos y objetivo</h2>
          </div>
          <div className="divide-y divide-gray-100">
            <Field label="Nombre">
              <input className="input-field w-56" value={form.full_name} onChange={(e) => set("full_name", e.target.value)} />
            </Field>
            <Field label="Sexo">
              <select className="input-field w-56" value={form.sex} onChange={(e) => set("sex", e.target.value)}>
                <option value="">—</option>
                <option value="male">Hombre</option>
                <option value="female">Mujer</option>
              </select>
            </Field>
            <Field label="Fecha de nacimiento">
              <input type="date" className="input-field w-56" value={form.birth_date} onChange={(e) => set("birth_date", e.target.value)} />
            </Field>
            <Field label="Altura (cm)">
              <input type="number" className="input-field w-56" value={form.height_cm} onChange={(e) => set("height_cm", e.target.value)} />
            </Field>
            <Field label="Peso actual (kg)">
              <input type="number" step="0.1" className="input-field w-56" value={form.current_weight_kg} onChange={(e) => set("current_weight_kg", e.target.value)} />
            </Field>
            <Field label="Actividad">
              <select className="input-field w-56" value={form.activity_level} onChange={(e) => set("activity_level", e.target.value)}>
                <option value="">—</option>
                {Object.entries(ACTIVITY_ES).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </Field>
            <Field label="Objetivo">
              <select className="input-field w-56" value={form.goal} onChange={(e) => set("goal", e.target.value)}>
                <option value="">—</option>
                {Object.entries(GOAL_ES).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </Field>
            <Field label="Peso objetivo (kg)">
              <input type="number" step="0.1" className="input-field w-56" value={form.target_weight_kg} onChange={(e) => set("target_weight_kg", e.target.value)} />
            </Field>
            <Field label="Ritmo (kg/semana)">
              <input type="number" step="0.05" className="input-field w-56" value={form.weekly_rate_kg} onChange={(e) => set("weekly_rate_kg", e.target.value)} />
            </Field>
            <Field label="Zona horaria">
              <input className="input-field w-56" value={form.timezone} onChange={(e) => set("timezone", e.target.value)} />
            </Field>
            <Field label="Restricciones">
              <input className="input-field w-56" placeholder="Separadas por comas" value={form.dietary_restrictions} onChange={(e) => set("dietary_restrictions", e.target.value)} />
            </Field>
            <Field label="Alergias">
              <input className="input-field w-56" placeholder="Separadas por comas" value={form.allergies} onChange={(e) => set("allergies", e.target.value)} />
            </Field>
          </div>
        </section>
      ) : (
        <>
          {/* Personal data */}
          <section className="card">
            <div className="card-header">
              <span className="text-lg">👤</span>
              <h2 className="font-bold text-gray-800">Datos personales</h2>
            </div>
            <Row label="Nombre" value={p.full_name ?? "—"} />
            <Row label="Sexo" value={p.sex ? SEX_ES[p.sex] : "—"} />
            <Row label="Fecha de nacimiento" value={p.birth_date ?? "—"} />
            <Row label="Altura" value={p.height_cm ? `${p.height_cm} cm` : "—"} />
            <Row label="Peso actual" value={p.current_weight_kg ? `${p.current_weight_kg} kg` : "—"} />
            <Row label="Actividad" value={p.activity_level ? ACTIVITY_ES[p.activity_level] : "—"} />
          </section>

          {/* Goals */}
          <section className="card">
            <div className="card-header">
              <span className="text-lg">🎯</span>
              <h2 className="font-bold text-gray-800">Objetivo</h2>
            </div>
            <Row label="Objetivo" value={p.goal ? GOAL_ES[p.goal] : "—"} />
            <Row label="Peso objetivo" value={p.target_weight_kg ? `${p.target_weight_kg} kg` : "—"} />
            <Row label="Ritmo" value={p.weekly_rate_kg ? `${p.weekly_rate_kg} kg/semana` : "—"} />
          </section>

          {/* Daily targets */}
          <section className="card">
            <div className="card-header">
              <span className="text-lg">📊</span>
              <h2 className="font-bold text-gray-800">Objetivos diarios</h2>
            </div>
            <Row label="🔥 Calorías" value={p.target_calories ? `${p.target_calories} kcal` : "—"} />
            <Row label="💪 Proteína" value={p.target_protein_g ? `${p.target_protein_g} g` : "—"} />
            <Row label="🍚 Carbohidratos" value={p.target_carbs_g ? `${p.target_carbs_g} g` : "—"} />
            <Row label="🧈 Grasas" value={p.target_fat_g ? `${p.target_fat_g} g` : "—"} />
          </section>

          {/* Preferences */}
          <section className="card">
            <div className="card-header">
              <span className="text-lg">⚙️</span>
              <h2 className="font-bold text-gray-800">Preferencias</h2>
            </div>
            <Row label="Restricciones" value={p.dietary_restrictions.join(", ") || "Ninguna"} />
            <Row label="Alergias" value={p.allergies.join(", ") || "Ninguna"} />
            <Row label="Zona horaria" value={p.timezone ?? "—"} />
          </section>
        </>
      )}

      {/* "A tener en cuenta" notes */}
      <section className="card">
        <div className="card-header">
          <span className="text-lg">🧠</span>
          <div>
            <h2 className="font-bold text-gray-800">A tener en cuenta</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Notas que NutriBot recuerda y usa al aconsejarte
            </p>
          </div>
        </div>
        {notes.length === 0 ? (
          <p className="py-3 text-sm text-gray-400">Todavía no hay notas. NutriBot las crea automáticamente al hablar contigo.</p>
        ) : (
          <ul className="space-y-2">
            {notes.map((n) => (
              <li key={n.id} className="flex items-center justify-between rounded-xl bg-gray-50/80 px-4 py-2.5 text-sm transition-colors hover:bg-gray-100">
                <div className="flex items-center gap-3">
                  <span className="badge-gray text-[11px]">
                    {NOTE_CATEGORY_ES[n.category] ?? n.category}
                  </span>
                  <span className="text-gray-700">{n.content}</span>
                </div>
                <button onClick={() => deleteNote(n.id)} className="btn-danger text-xs">
                  🗑️ Eliminar
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-4 flex gap-2">
          <select className="input-field w-44" value={newCategory} onChange={(e) => setNewCategory(e.target.value)}>
            {Object.entries(NOTE_CATEGORY_ES).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <input
            className="input-field flex-1"
            placeholder="Ej. No le gusta la pera"
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addNote()}
          />
          <button onClick={addNote} className="btn-primary whitespace-nowrap">➕ Añadir</button>
        </div>
      </section>

      {/* Danger zone */}
      <section className="rounded-2xl border-2 border-red-200 bg-red-50/50 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-bold text-red-700">⚠️ Zona peligrosa</h2>
            <p className="text-xs text-red-500 mt-0.5">
              Borra tu cuenta y todos tus datos de forma permanente. No se puede deshacer.
            </p>
          </div>
          <button onClick={deleteAccount} className="rounded-xl border-2 border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-100 transition-all duration-200">
            Eliminar perfil
          </button>
        </div>
      </section>
    </div>
  );
}
