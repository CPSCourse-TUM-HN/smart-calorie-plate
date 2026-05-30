"use client"

import { useState } from "react"
import { Activity, ArrowRight, ChevronDown, Sparkles } from "lucide-react"

export type Profile = {
  age: string
  gender: string
  height: string
  weight: string
  activity: string
  diet: string
}

const fieldClass =
  "h-12 w-full rounded-xl border border-zinc-800 bg-zinc-900/60 px-4 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none transition-all duration-200 focus:border-emerald-500/60 focus:bg-zinc-900 focus:ring-4 focus:ring-emerald-500/10"

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-medium uppercase tracking-wider text-zinc-500">{label}</label>
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
      <ChevronDown className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
    </div>
  )
}

export function SetupScreen({ onSubmit }: { onSubmit: (p: Profile) => void }) {
  const [profile, setProfile] = useState<Profile>({
    age: "21",
    gender: "female",
    height: "170",
    weight: "65",
    activity: "light",
    diet: "fatloss",
  })

  const set = (key: keyof Profile, value: string) =>
    setProfile((p) => ({ ...p, [key]: value }))

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-zinc-950 px-4 py-12">
      {/* ambient glow */}
      <div className="pointer-events-none absolute left-1/2 top-0 h-[40rem] w-[40rem] -translate-x-1/2 -translate-y-1/3 rounded-full bg-emerald-600/10 blur-3xl" />

      <div className="relative w-full max-w-md rounded-3xl border border-zinc-800 bg-zinc-900/40 p-8 shadow-2xl shadow-black/60 backdrop-blur-xl">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-500/30 bg-emerald-500/10">
            <Sparkles className="h-6 w-6 text-emerald-400" />
          </div>
          <h1 className="text-balance text-2xl font-bold tracking-tight text-zinc-50">
            Smart Plate Setup
          </h1>
          <p className="mt-2 text-sm text-zinc-500">Enter your body metrics to generate a personalized nutrition goal</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Age">
            <input
              type="number"
              value={profile.age}
              onChange={(e) => set("age", e.target.value)}
              className={fieldClass}
            />
          </Field>

          <Field label="Gender">
            <NativeSelect value={profile.gender} onChange={(v) => set("gender", v)}>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </NativeSelect>
          </Field>

          <Field label="Height (cm)">
            <input
              type="number"
              value={profile.height}
              onChange={(e) => set("height", e.target.value)}
              className={fieldClass}
            />
          </Field>

          <Field label="Weight (kg)">
            <input
              type="number"
              value={profile.weight}
              onChange={(e) => set("weight", e.target.value)}
              className={fieldClass}
            />
          </Field>

          <div className="col-span-2">
            <Field label="Activity Level">
              <NativeSelect value={profile.activity} onChange={(v) => set("activity", v)}>
                <option value="sedentary">Sedentary</option>
                <option value="light">Lightly Active</option>
                <option value="moderate">Moderately Active</option>
                <option value="active">Very Active</option>
              </NativeSelect>
            </Field>
          </div>

          <div className="col-span-2">
            <Field label="Diet Mode">
              <NativeSelect value={profile.diet} onChange={(v) => set("diet", v)}>
                <option value="fatloss">Fat Loss</option>
                <option value="maintain">Maintain</option>
                <option value="bulk">Bulk</option>
              </NativeSelect>
            </Field>
          </div>
        </div>

        <button
          onClick={() => onSubmit(profile)}
          className="group mt-8 flex h-13 w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-emerald-600/20 transition-all duration-200 hover:bg-emerald-500 hover:shadow-emerald-500/30 active:scale-[0.98]"
        >
          <Activity className="h-4 w-4" />
          Calculate Goal &amp; Enter Dashboard
          <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
        </button>
      </div>
    </main>
  )
}
