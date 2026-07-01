export interface AdminUser {
  id: number;
  telegram_id: number | null;
  full_name: string | null;
  email: string | null;
  role: "client" | "admin";
  is_active: boolean;
  onboarding_completed_at: string | null;
  created_at: string;
}

export interface UsagePoint {
  date: string;
  tokens_prompt: number;
  tokens_completion: number;
  cost_usd: number;
}

export interface UsageMetrics {
  days: number;
  tokens_prompt: number;
  tokens_completion: number;
  tokens_total: number;
  assistant_messages: number;
  estimated_cost_usd: number;
  prices_per_mtok: { input: number; output: number };
  series: UsagePoint[];
}

export interface KnowledgeDoc {
  id: number;
  title: string;
  source: string | null;
  source_url: string | null;
  status: string;
  chunk_count: number;
  indexed_at: string | null;
  created_at: string;
}

export interface LegalDoc {
  id: number;
  doc_type: string;
  version: number;
  content: string;
  is_active: boolean;
  created_at: string;
}
