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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Términos legales</h1>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold">Editar y publicar nueva versión</h2>
        <form onSubmit={publish} className="space-y-3">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={12}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy || !content.trim()}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {busy ? "Publicando…" : "Publicar nueva versión"}
          </button>
        </form>
      </section>

      <section className="overflow-x-auto rounded-xl bg-white shadow">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-4 py-3">Versión</th>
              <th className="px-4 py-3">Tipo</th>
              <th className="px-4 py-3">Activa</th>
              <th className="px-4 py-3">Creada</th>
              <th className="px-4 py-3">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id} className="border-b last:border-0">
                <td className="px-4 py-3">v{d.version}</td>
                <td className="px-4 py-3">{d.doc_type}</td>
                <td className="px-4 py-3">{d.is_active ? "✅" : "—"}</td>
                <td className="px-4 py-3 text-gray-500">
                  {new Date(d.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3">
                  {!d.is_active && (
                    <button
                      onClick={() => activate(d.id)}
                      className="rounded border px-2 py-1 text-xs hover:bg-gray-50"
                    >
                      Activar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
