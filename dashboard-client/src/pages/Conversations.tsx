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
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Conversaciones</h1>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-[220px_1fr]">
        <aside className="rounded-xl bg-white p-2 shadow">
          {conversations.length === 0 && (
            <p className="p-3 text-sm text-gray-500">Sin conversaciones aún.</p>
          )}
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelected(c.id)}
              className={`mb-1 w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                selected === c.id ? "bg-brand/10 font-medium" : "hover:bg-gray-50"
              }`}
            >
              <div>{c.title || `Conversación #${c.id}`}</div>
              <div className="text-xs text-gray-400">
                {new Date(c.created_at).toLocaleDateString()} · {c.message_count} msgs
              </div>
            </button>
          ))}
        </aside>

        <section className="rounded-xl bg-white p-4 shadow">
          {messages.length === 0 ? (
            <p className="text-sm text-gray-500">Selecciona una conversación.</p>
          ) : (
            <div className="space-y-3">
              {messages
                .filter((m) => m.role === "user" || m.role === "assistant")
                .map((m, i) => (
                  <div
                    key={i}
                    className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
                        m.role === "user"
                          ? "bg-brand text-white"
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
