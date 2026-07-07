"use client"

import { useState } from "react"
import { Activity, ArrowRight, ChevronDown, Loader2, Sparkles } from "lucide-react"
import {
  computeTargetsLocal,
  createUserProfile,
  type NutritionTargets,
} from "@/lib/api"

export type Profile = {
  name: string
  age: string
  gender: string
  height: string
  weight: string
  activity: string
  diet: string
  // Added after submit: account id (only when the backend write succeeds)
  // plus the computed nutrition targets
  userId: number | null
  targets: NutritionTargets
}

const fieldClass =
  "h-12 w-full rounded-xl border border-zinc-800 bg-zinc-900/60 px-4 text-sm text-zinc-100 placeholder:text-zinc-500 outline-none transition-all duration-200 focus:border-emerald-500/60 focus:bg-zinc-900 focus:ring-4 focus:ring-emerald-500/10"

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-medium uppercase tracking-wider text-zinc-400">{label}</label>
      {children}
    </div>
  )
}

function NativeSelect({
  value,
  onChange,
  children,
}: {
  value: string
  onChange: (v: string) => void
  children: React.ReactNode
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-12 w-full cursor-pointer appearance-none rounded-xl border border-zinc-800 bg-zinc-900/60 px-4 pr-10 text-sm text-zinc-100 outline-none transition-all duration-200 focus:border-emerald-500/60 focus:bg-zinc-900 focus:ring-4 focus:ring-emerald-500/10 [&>option]:bg-zinc-900 [&>option]:text-zinc-100"
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
    </div>
  )
}

type Form = Pick<Profile, "name" | "age" | "gender" | "height" | "weight" | "activity" | "diet">

export function SetupScreen({ onSubmit }: { onSubmit: (p: Profile) => void }) {
  const [form, setForm] = useState<Form>({
    name: "",
    age: "21",
    gender: "female",
    height: "170",
    weight: "65",
    activity: "light",
    diet: "fatloss",
  })
  const [loading, setLoading] = useState(false)
  const [note, setNote] = useState<string | null>(null)

  const set = (key: keyof Form, value: string) =>
    setForm((p) => ({ ...p, [key]: value }))

  const handleSubmit = async () => {
    if (loading) return
    setLoading(true)
    setNote(null)

    // Generate a random default name when the username is left blank.
    const name = form.name.trim() || `Guest-${Math.floor(1000 + Math.random() * 9000)}`

    const input = {
      name,
      age: Number(form.age) || 0,
      gender: form.gender,
      height_cm: Number(form.height) || 0,
      weight_kg: Number(form.weight) || 0,
      activity_level: form.activity,
      diet_mode: form.diet,
    }

    let userId: number | null = null
    let targets: NutritionTargets

    try {
      const res = await createUserProfile(input)
      targets = res.targets
      userId = res.user_profile?.id ?? null
    } catch (e) {
      // Never block navigation when the backend is down: compute the
      // targets locally and proceed to the Dashboard as usual.
      targets = computeTargetsLocal(input)
      setNote("Offline mode: backend not connected, using locally computed targets.")
    }

    // Always navigate, online or not — this is the key fix for the
    // "packaged app cannot navigate" issue.
    onSubmit({ ...form, name, userId, targets })
    setLoading(false)
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-zinc-950 px-4 py-12">
      <div className="pointer-events-none absolute left-1/2 top-0 h-[40rem] w-[40rem] -translate-x-1/2 -translate-y-1/3 rounded-full bg-emerald-600/10 blur-3xl" />

      <div className="relative w-full max-w-md rounded-3xl border border-zinc-800 bg-zinc-900/40 p-8 shadow-2xl shadow-black/60 backdrop-blur-xl">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-500/30 bg-emerald-500/10">
            <Sparkles className="h-6 w-6 text-emerald-400" />
          </div>
          <h1 className="text-balance text-2xl font-bold tracking-tight text-zinc-50">
            Smart Plate Setup
          </h1>
          <p className="mt-2 text-sm text-zinc-400">Enter your body metrics to generate a personalized nutrition goal</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <Field label="Username">
              <input
                type="text"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="Optional — leave blank for a random name"
                className={fieldClass}
              />
            </Field>
          </div>

          <Field label="Age">
            <input
              type="number"
              value={form.age}
              onChange={(e) => set("age", e.target.value)}
              className={fieldClass}
            />
          </Field>

          <Field label="Gender">
            <NativeSelect value={form.gender} onChange={(v) => set("gender", v)}>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </NativeSelect>
          </Field>

          <Field label="Height (cm)">
            <input
              type="number"
              value={form.height}
              onChange={(e) => set("height", e.target.value)}
              className={fieldClass}
            />
          </Field>

          <Field label="Weight (kg)">
            <input
              type="number"
              value={form.weight}
              onChange={(e) => set("weight", e.target.value)}
              className={fieldClass}
            />
          </Field>

          <div className="col-span-2">
            <Field label="Activity Level">
              <NativeSelect value={form.activity} onChange={(v) => set("activity", v)}>
                <option value="sedentary">Sedentary</option>
                <option value="light">Lightly Active</option>
                <option value="moderate">Moderately Active</option>
                <option value="active">Very Active</option>
              </NativeSelect>
            </Field>
          </div>

          <div className="col-span-2">
            <Field label="Diet Mode">
              <NativeSelect value={form.diet} onChange={(v) => set("diet", v)}>
                <option value="fatloss">Fat Loss</option>
                <option value="maintain">Maintain</option>
                <option value="bulk">Bulk</option>
              </NativeSelect>
            </Field>
          </div>
        </div>

        {note && (
          <p className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
            {note}
          </p>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="group mt-8 flex h-13 w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-emerald-600/20 transition-all duration-200 hover:bg-emerald-500 hover:shadow-emerald-500/30 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Calculating...
            </>
          ) : (
            <>
              <Activity className="h-4 w-4" />
              Calculate Goal &amp; Enter Dashboard
              <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
            </>
          )}
        </button>
      </div>
    </main>
  )
}
