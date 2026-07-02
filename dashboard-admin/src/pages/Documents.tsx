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
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
          Documentos RAG
        </h1>
        <p className="mt-1 text-sm text-gray-500">Base de conocimiento para las respuestas de NutriBot</p>
      </div>

      {/* Add document form */}
      <section className="card">
        <div className="card-header">
          <span className="text-lg">📝</span>
          <h2 className="font-bold text-gray-800">Añadir documento</h2>
        </div>
        <form onSubmit={create} className="space-y-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Título del documento"
            className="input-field w-full"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Contenido del documento…"
            rows={6}
            className="input-field w-full"
          />
          {error && (
            <div className="rounded-xl border-2 border-red-200 bg-red-50 p-3 text-sm text-red-600">
              ⚠️ {error}
            </div>
          )}
          <button
            type="submit"
            disabled={busy || !title || !content}
            className="btn-primary inline-flex items-center gap-2"
          >
            {busy ? "⏳ Indexando…" : "📤 Indexar documento"}
          </button>
        </form>
      </section>

      {/* Documents table */}
      <div className="overflow-x-auto rounded-2xl border-2 border-gray-100 bg-white shadow-sm">
        <table className="admin-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Título</th>
              <th>Estado</th>
              <th>Chunks</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td className="font-mono text-xs text-gray-400">#{d.id}</td>
                <td className="font-semibold">{d.title}</td>
                <td>
                  <span className={d.status === "indexed" ? "badge-green" : "badge-gray"}>
                    {d.status === "indexed" ? "✅ Indexado" : d.status}
                  </span>
                </td>
                <td className="font-mono text-sm">{d.chunk_count}</td>
                <td>
                  <div className="flex gap-2">
                    <button onClick={() => reindex(d.id)} className="btn-ghost text-xs">
                      🔄 Reindexar
                    </button>
                    <button onClick={() => remove(d.id)} className="btn-danger text-xs">
                      🗑️ Borrar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr>
                <td colSpan={5} className="py-10 text-center text-gray-400">
                  <span className="text-2xl">📭</span>
                  <p className="mt-2">No hay documentos. ¡Añade el primero!</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
