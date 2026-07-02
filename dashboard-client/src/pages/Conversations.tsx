import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Conversation, Message } from "../types";

export default function Conversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    api.get<Conversation[]>("/me/conversations").then((r) => {
      setConversations(r.data);
      if (r.data.length > 0) setSelected(r.data[0].id);
    });
  }, []);

  useEffect(() => {
    if (selected === null) return;
    api
      .get<Message[]>(`/me/conversations/${selected}/messages`)
      .then((r) => setMessages(r.data));
  }, [selected]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold bg-gradient-to-r from-green-600 to-emerald-500 bg-clip-text text-transparent">
          Conversaciones
        </h1>
        <p className="mt-0.5 text-sm text-gray-500">Historial de tus chats con NutriBot</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-[240px_1fr]">
        {/* Conversations list */}
        <aside className="card p-2 max-h-[70vh] overflow-y-auto">
          {conversations.length === 0 && (
            <p className="p-4 text-sm text-gray-400">Sin conversaciones aún.</p>
          )}
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelected(c.id)}
              className={`mb-1 w-full rounded-xl px-4 py-3 text-left transition-all duration-200 ${
                selected === c.id
                  ? "bg-green-100 font-semibold text-green-800 shadow-sm"
                  : "hover:bg-gray-100 text-gray-700"
              }`}
            >
              <div className="font-medium">{c.title || `Conversación #${c.id}`}</div>
              <div className="mt-0.5 flex items-center gap-2 text-xs text-gray-400">
                <span>{new Date(c.created_at).toLocaleDateString()}</span>
                <span>·</span>
                <span>{c.message_count} msgs</span>
              </div>
            </button>
          ))}
        </aside>

        {/* Messages */}
        <section className="card max-h-[70vh] overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <span className="text-4xl">💬</span>
              <p className="mt-3">Selecciona una conversación</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages
                .filter((m) => m.role === "user" || m.role === "assistant")
                .map((m, i) => (
                  <div
                    key={i}
                    className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-5 py-3 text-sm leading-relaxed shadow-sm ${
                        m.role === "user"
                          ? "bg-gradient-to-br from-green-600 to-emerald-600 text-white"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {m.content}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
