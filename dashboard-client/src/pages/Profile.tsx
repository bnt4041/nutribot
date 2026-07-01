import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Profile as ProfileType } from "../types";

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

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-gray-100 py-2 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

export default function Profile() {
  const [profile, setProfile] = useState<ProfileType | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .get<ProfileType>("/me")
      .then((r) => setProfile(r.data))
      .catch(() => setError(true));
  }, []);

  if (error) return <p className="text-red-600">No se pudo cargar el perfil.</p>;
  if (!profile) return <p className="text-gray-500">Cargando…</p>;

  const dash = (v: unknown) => (v === null || v === undefined ? "—" : String(v));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tu perfil</h1>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold">Datos personales</h2>
        <Row label="Nombre" value={dash(profile.full_name)} />
        <Row label="Sexo" value={profile.sex ? SEX_ES[profile.sex] : "—"} />
        <Row label="Fecha de nacimiento" value={dash(profile.birth_date)} />
        <Row label="Altura" value={profile.height_cm ? `${profile.height_cm} cm` : "—"} />
        <Row
          label="Peso actual"
          value={profile.current_weight_kg ? `${profile.current_weight_kg} kg` : "—"}
        />
        <Row
          label="Actividad"
          value={profile.activity_level ? ACTIVITY_ES[profile.activity_level] : "—"}
        />
      </section>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold">Objetivo</h2>
        <Row label="Objetivo" value={profile.goal ? GOAL_ES[profile.goal] : "—"} />
        <Row
          label="Peso objetivo"
          value={profile.target_weight_kg ? `${profile.target_weight_kg} kg` : "—"}
        />
        <Row
          label="Ritmo"
          value={
            profile.weekly_rate_kg ? `${profile.weekly_rate_kg} kg/semana` : "—"
          }
        />
      </section>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold">Objetivos diarios</h2>
        <Row label="Calorías" value={profile.target_calories ? `${profile.target_calories} kcal` : "—"} />
        <Row label="Proteína" value={profile.target_protein_g ? `${profile.target_protein_g} g` : "—"} />
        <Row label="Carbohidratos" value={profile.target_carbs_g ? `${profile.target_carbs_g} g` : "—"} />
        <Row label="Grasas" value={profile.target_fat_g ? `${profile.target_fat_g} g` : "—"} />
      </section>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold">Preferencias</h2>
        <Row
          label="Restricciones"
          value={profile.dietary_restrictions.join(", ") || "Ninguna"}
        />
        <Row label="Alergias" value={profile.allergies.join(", ") || "Ninguna"} />
        <Row label="Zona horaria" value={dash(profile.timezone)} />
      </section>
    </div>
  );
}
