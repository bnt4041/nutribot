import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import { KnowledgeDoc } from "../types";

export default function Documents() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    api.get<KnowledgeDoc[]>("/knowledge/documents").then((r) => setDocs(r.data));

  useEffect(() => {
    load();
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/knowledge/documents", { title, content });
      setTitle("");
      setContent("");
      await load();
    } catch {
      setError("No se pudo indexar el documento.");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    await api.delete(`/knowledge/documents/${id}`);
    load();
  };

  const reindex = async (id: number) => {
    await api.post(`/knowledge/documents/${id}/reindex`);
    load();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Documentos RAG</h1>

      <section className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold">Añadir documento</h2>
        <form onSubmit={create} className="space-y-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Título"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand focus:outline-none"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Contenido del documento…"
            rows={6}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand focus:outline-none"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={busy || !title || !content}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {busy ? "Indexando…" : "Indexar documento"}
          </button>
        </form>
      </section>

      <section className="overflow-x-auto rounded-xl bg-white shadow">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Título</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Chunks</th>
              <th className="px-4 py-3">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id} className="border-b last:border-0">
                <td className="px-4 py-3">{d.id}</td>
                <td className="px-4 py-3">{d.title}</td>
                <td className="px-4 py-3">{d.status}</td>
                <td className="px-4 py-3">{d.chunk_count}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      onClick={() => reindex(d.id)}
                      className="rounded border px-2 py-1 text-xs hover:bg-gray-50"
                    >
                      Reindexar
                    </button>
                    <button
                      onClick={() => remove(d.id)}
                      className="rounded border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                    >
                      Borrar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                  No hay documentos.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
