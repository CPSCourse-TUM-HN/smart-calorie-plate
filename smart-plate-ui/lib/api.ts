// Unified backend API client.
//
// Base URL strategy (works for both dev and packaged runs):
//   1. If NEXT_PUBLIC_API_BASE is set, it wins.
//   2. Otherwise, if the page runs on :3000 (next dev), the backend is at
//      127.0.0.1:8000.
//   3. Otherwise same-origin (packaged app: FastAPI serves the frontend on
//      the same port), so relative paths are used.
function resolveBase(): string {
  const env = process.env.NEXT_PUBLIC_API_BASE
  if (env) return env.replace(/\/$/, "")
  if (typeof window !== "undefined" && window.location.port === "3000") {
    return "http://127.0.0.1:8000"
  }
  return ""
}

export const API_BASE = typeof window !== "undefined" ? resolveBase() : ""

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${resolveBase()}${path}`, init)
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type NutritionTargets = {
  target_calories: number
  target_protein_g: number
  target_fat_g: number
  target_carbs_g: number
}

export type UserProfileRecord = NutritionTargets & {
  id: number
  name: string | null
  age: number
  gender: string
  height_cm: number
  weight_kg: number
  activity_level: number
  diet_mode: string
}

export type Detection = {
  food_id: number
  name_en: string
  name_zh: string | null
  confidence: number
  weight_g?: number
}

export type AnalyzedItem = {
  food_id: number
  name_en: string
  name_zh: string | null
  weight_g: number
  kcal: number
  protein: number
  carbs: number
  fat: number
}

export type AnalyzeResult = {
  total_kcal: number
  total_protein: number
  total_carbs: number
  total_fat: number
  items: AnalyzedItem[]
  advice: string[]
  detections?: Detection[]
}

export type MealRecord = {
  id: number
  user_id: number | null
  log_date: string
  created_at: string
  total_kcal: number
  total_protein_g: number
  total_carbs_g: number
  total_fat_g: number
  items: AnalyzedItem[]
  advice: string | null
}

export type DaySummary = {
  date: string
  meal_count: number
  total_kcal: number
  total_protein_g: number
  total_carbs_g: number
  total_fat_g: number
}

export type Recommendation = {
  remaining: { calories: number; protein_g: number; carbs_g: number; fat_g: number }
  tips: string[]
  suggested_foods: {
    food_id: number
    name_zh: string
    name_en: string
    kcal_per_100g: number
    protein_per_100g: number
    carbs_per_100g: number
    fat_per_100g: number
  }[]
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------
export function createUserProfile(input: {
  name?: string
  age: number
  gender: string
  height_cm: number
  weight_kg: number
  activity_level: string
  diet_mode: string
}) {
  return request<{ user_profile: UserProfileRecord; targets: NutritionTargets }>(
    "/api/user-profile/",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  )
}

export function listUserProfiles() {
  return request<UserProfileRecord[]>("/api/user-profiles/")
}

export function deleteUserProfile(userId: number) {
  return request<{ ok: boolean; deleted_id: number }>(`/api/user-profile/${userId}`, {
    method: "DELETE",
  })
}

export function detectMeal(file: File, conf = 0.25) {
  const form = new FormData()
  form.append("image", file)
  return request<{ detections: Detection[] }>(`/meal/detect?conf=${conf}`, {
    method: "POST",
    body: form,
  })
}

export function analyzeByIds(items: { food_id: number; weight_g: number }[]) {
  return request<AnalyzeResult>("/meal/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  })
}

export function createMeal(payload: {
  user_id: number | null
  total_kcal: number
  total_protein_g: number
  total_carbs_g: number
  total_fat_g: number
  items: AnalyzedItem[]
  advice?: string | null
}) {
  return request<MealRecord>("/api/meals/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

export function listMeals(userId: number | null, onDate?: string) {
  const params = new URLSearchParams()
  if (userId != null) params.set("user_id", String(userId))
  if (onDate) params.set("on_date", onDate)
  const qs = params.toString()
  return request<MealRecord[]>(`/api/meals/${qs ? `?${qs}` : ""}`)
}

export function getDaySummary(userId: number | null, onDate?: string) {
  const params = new URLSearchParams()
  if (userId != null) params.set("user_id", String(userId))
  if (onDate) params.set("on_date", onDate)
  const qs = params.toString()
  return request<DaySummary>(`/api/meals/summary${qs ? `?${qs}` : ""}`)
}

// Local fallback: compute the targets client-side when the backend is
// unavailable, so the page can always reach the Dashboard. Uses the same
// formulas as utils.calculate_nutrition_targets on the backend.
const ACTIVITY_FACTOR: Record<string, number> = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
}

export function computeTargetsLocal(input: {
  age: number
  gender: string
  height_cm: number
  weight_kg: number
  activity_level: string
  diet_mode: string
}): NutritionTargets {
  const { age, gender, height_cm, weight_kg } = input
  const factor = ACTIVITY_FACTOR[input.activity_level] ?? 1.375
  const bmr =
    gender.toLowerCase() === "male"
      ? 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
      : 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
  const tdee = bmr * factor

  const diet = input.diet_mode
  let calories = tdee
  if (diet === "fatloss") calories = tdee - 400
  else if (diet === "bulk") calories = tdee + 300

  const protein = (diet === "fatloss" || diet === "bulk" ? 2.0 : 1.8) * weight_kg
  const fat = 0.9 * weight_kg
  const carbs = Math.max(0, (calories - (protein * 4 + fat * 9)) / 4)

  const r = (n: number) => Math.round(n * 10) / 10
  return {
    target_calories: r(calories),
    target_protein_g: r(protein),
    target_fat_g: r(fat),
    target_carbs_g: r(carbs),
  }
}

export function getRecommendation(payload: {
  target_calories: number
  target_protein_g: number
  target_carbs_g: number
  target_fat_g: number
  actual_calories: number
  actual_protein_g: number
  actual_carbs_g: number
  actual_fat_g: number
}) {
  return request<Recommendation>("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}
