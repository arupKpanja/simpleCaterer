// Types mirroring the backend Part 1 API payloads.

export interface Requirements {
  event_type: string;
  guest_count: number;
  budget: number;
  dietary_restrictions: string[];
  cuisine_pref?: string;
  location?: string;
  event_date?: string;
  session_id?: string;
}

export interface Course {
  course: string;
  dish_id: number;
  dish: string;
  cuisine: string;
  diet_tags: string[];
  allergens: string[];
  serving_cost: number;
}

export interface NamedCost {
  name: string;
  cost: number;
}

export interface ShoppingLine {
  item: string;
  unit: string;
  qty: number;
  price_per_unit: number;
  line_cost: number;
  stock_qty: number;
  short_by: number;
  allergens: string[];
}

export interface Option {
  id?: string;
  tier: "essential" | "standard" | "premium" | string;
  theme: string;
  courses: Course[];
  decor: NamedCost;
  venue: NamedCost & { capacity?: number; note?: string };
  food_cost: number;
  decor_cost: number;
  venue_cost: number;
  total_cost: number;
  per_guest: number;
  within_budget: boolean;
  overage: number;
  allergen_safe: boolean;
  shopping_list: ShoppingLine[];
  // present on the live plan payload; absent on a frozen order snapshot
  budget?: number;
  dietary_restrictions?: string[];
  event_type?: string;
  guest_count?: number;
}

export interface ApprovedOrder {
  order_id: string;
  event_id: string;
  option_id: string;
  tier: string;
  status: string;
  total_cost: number;
  per_guest: number;
  guest_count: number;
  approved_at: string;
  snapshot: Option;
}

export interface VendorLine {
  item: string;
  unit: string;
  qty: number;
  unit_price: number;
  line_cost: number;
}

export interface StockImpactLine {
  item: string;
  required: number;
  consumed: number;
  short_by: number;
  stock_after: number;
}

export interface VendorOrder {
  vendor_order_id: string;
  approved_order_id: string;
  status: string; // draft | awaiting_approval | placed | rejected
  total: number;
  created_at: string;
  decided_at: string | null;
  lines: VendorLine[];
  stock_impact: StockImpactLine[];
  shopping_list: VendorLine[];
}

export interface PlanResult {
  type: "result";
  session_id: string;
  event_id?: string;
  options: Option[];
  errors: string[];
  log: { stage: string; message: string }[];
}

export interface StageEvent {
  type: "stage";
  node: string;
  stage: string;
  message: string;
}

export type PlanEvent = StageEvent | PlanResult;

export interface Health {
  status: string;
  llm: "ollama" | "fallback" | string;
}

export interface StoredEvent {
  event_id: string;
  requirements: Requirements;
  created_at: string;
  options: Option[];
}
