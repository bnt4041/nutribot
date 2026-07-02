export interface Profile {
  full_name: string | null;
  email: string | null;
  telegram_id: number | null;
  onboarding_completed: boolean;
  sex: string | null;
  birth_date: string | null;
  height_cm: number | null;
  current_weight_kg: number | null;
  target_weight_kg: number | null;
  weekly_rate_kg: number | null;
  activity_level: string | null;
  goal: string | null;
  timezone: string | null;
  dietary_restrictions: string[];
  allergies: string[];
  target_calories: number | null;
  target_protein_g: number | null;
  target_carbs_g: number | null;
  target_fat_g: number | null;
}

export interface Macros {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface DailySummary {
  date: string;
  timezone: string;
  totals: Macros;
  targets: Macros | null;
  remaining: Macros | null;
  meals: Meal[];
}

export interface Meal {
  food_name: string;
  quantity_g: number | null;
  meal_type: string | null;
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
}

export interface HistoryPoint {
  date: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface WeightPoint {
  logged_at: string;
  weight_kg: number;
}

export interface DietPlanItem {
  id: number;
  scheduled_date: string | null;
  meal_type: string | null;
  scheduled_time: string | null;
  title: string;
  description: string | null;
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  status: string;
  source: string;
}

export interface Note {
  id: number;
  category: string;
  content: string;
  source: string;
}

export interface Conversation {
  id: number;
  title: string | null;
  created_at: string;
  message_count: number;
}

export interface Message {
  role: string;
  content: string;
  created_at: string;
}
