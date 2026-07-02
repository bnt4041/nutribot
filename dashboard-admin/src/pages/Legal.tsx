import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import { LegalDoc } from "../types";

export default function Legal() {
  const [docs, setDocs] = useState<LegalDoc[]>([]);
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () =>
    api.get<LegalDoc[]>("/admin/legal").then((r) => {
      setDocs(r.data);
      const activeTerms = r.data.find(
        (d) => d.doc_type === "terms" && d.is_active,
      );
      if (activeTerms && !content) setContent(activeTerms.content);
    });

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const publish = async (e: FormEvent) => {
    e.preventDefault();
    if (
      !confirm(
        "Publicar una nueva versión hará que los usuarios deban aceptarla de nuevo. ¿Continuar?",
      )
    )
      return;
    setBusy(true);
    try {
      await api.post("/admin/legal", {
        doc_type: "terms",
        content,
        activate: true,
      });
      await load();
    } finally {
      setBusy(false);
    }
  };

  const activate = async (id: number) => {
    await api.patch(`/admin/legal/${id}/activate`);
    load();
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
          Términos legales
        </h1>
        <p className="mt-1 text-sm text-gray-500">Gestiona los términos que los usuarios deben aceptar</p>
      </div>

      {/* Editor */}
      <section className="card">
        <div className="card-header">
          <span className="text-lg">✍️</span>
          <h2 className="font-bold text-gray-800">Editar y publicar nueva versión</h2>
        </div>
        <form onSubmit={publish} className="space-y-4">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={14}
            className="input-field w-full font-mono text-sm"
            placeholder="Escribe aquí los términos legales…"
          />
          <button
            type="submit"
            disabled={busy || !content.trim()}
            className="btn-primary inline-flex items-center gap-2"
          >
            {busy ? "⏳ Publicando…" : "📋 Publicar nueva versión"}
          </button>
        </form>
      </section>

      {/* Version history */}
      <div className="overflow-x-auto rounded-2xl border-2 border-gray-100 bg-white shadow-sm">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Versión</th>
              <th>Tipo</th>
              <th>Activa</th>
              <th>Creada</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td className="font-semibold">v{d.version}</td>
                <td>
                  <span className="badge-gray">{d.doc_type}</span>
                </td>
                <td>
                  {d.is_active ? (
                    <span className="badge-green">✅ Activa</span>
                  ) : (
                    <span className="badge-gray">—</span>
                  )}
                </td>
                <td className="text-gray-500 text-xs">
                  {new Date(d.created_at).toLocaleDateString()}
                </td>
                <td>
                  {!d.is_active && (
                    <button onClick={() => activate(d.id)} className="btn-ghost text-xs">
                      🔓 Activar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
