"use client"

import { useState } from "react"
import {
  Camera,
  CircleCheck,
  Flame,
  Info,
  LayoutDashboard,
  LogOut,
  NotebookPen,
  Settings,
  UtensilsCrossed,
  Zap,
} from "lucide-react"
import { MacroDonut } from "@/components/macro-donut"
import type { Profile } from "@/components/setup-screen"

const DIET_LABELS: Record<string, string> = {
  fatloss: "Fat Loss Phase",
  maintain: "Maintenance Phase",
  bulk: "Bulking Phase",
}

const MACROS = [
  { key: "carb", name: "Carbs", grams: 190, goal: 210, color: "#3b82f6" },
  { key: "protein", name: "Protein", grams: 100, goal: 120, color: "#ec4899" },
  { key: "fat", name: "Fat", grams: 50, goal: 55, color: "#eab308" },
]

function MacroBar({
  name,
  grams,
  goal,
  color,
}: {
  name: string
  grams: number
  goal: number
  color: string
}) {
  const pct = Math.min(100, Math.round((grams / goal) * 100))
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-2 font-medium text-zinc-300">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
          {name}
        </span>
        <span className="tabular-nums text-zinc-500">
          {grams}g <span className="text-zinc-700">/ {goal}g</span>
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-zinc-800">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

function NavItem({
  icon: Icon,
  label,
  active,
}: {
  icon: typeof LayoutDashboard
  label: string
  active?: boolean
}) {
  return (
    <button
      className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all duration-200 ${
        active
          ? "bg-zinc-800/80 text-zinc-50"
          : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200"
      }`}
    >
      <Icon className="h-4.5 w-4.5" />
      {label}
    </button>
  )
}

export function Dashboard({ profile, onReset }: { profile: Profile; onReset: () => void }) {
  const [recognized, setRecognized] = useState(false)
  const dietLabel = DIET_LABELS[profile.diet] ?? "Fat Loss Phase"
  const donutData = MACROS.map((m) => ({ name: m.name, value: m.grams, color: m.color }))

  return (
    <div className="flex min-h-screen flex-col bg-zinc-950 text-zinc-100 lg:h-screen lg:flex-row lg:overflow-hidden">
      {/* Left sidebar */}
      <aside className="flex w-full shrink-0 flex-col gap-6 border-b border-zinc-900 p-5 lg:w-72 lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-2.5 px-1.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600 shadow-lg shadow-emerald-600/30">
            <UtensilsCrossed className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-zinc-50">Smart Plate</span>
        </div>

        {/* User status card */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-zinc-100">User 1</span>
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400">
              {dietLabel}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-3 rounded-xl bg-zinc-950/60 p-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-500/10">
              <Flame className="h-4.5 w-4.5 text-orange-400" />
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] uppercase tracking-wider text-zinc-500">Daily Goal</span>
              <span className="text-base font-bold tabular-nums text-zinc-50">
                1517 <span className="text-xs font-normal text-zinc-500">kcal</span>
              </span>
            </div>
          </div>
        </div>

        <nav className="flex flex-col gap-1">
          <NavItem icon={LayoutDashboard} label="Dashboard" active />
          <NavItem icon={NotebookPen} label="Diet Notes" />
          <NavItem icon={Zap} label="Nutrition Analysis" />
          <NavItem icon={Settings} label="Account Settings" />
        </nav>

        <button
          onClick={onReset}
          className="mt-auto flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium text-zinc-500 transition-all duration-200 hover:bg-zinc-900 hover:text-zinc-200"
        >
          <LogOut className="h-4.5 w-4.5" />
          Log Out / Reset
        </button>
      </aside>

      {/* Center main view */}
      <section className="flex flex-1 flex-col gap-5 p-5 lg:overflow-y-auto lg:p-8">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-zinc-50">Image Recognition Workbench</h2>
          <p className="mt-1 text-sm text-zinc-500">Point the camera at your plate and AI will detect foods and estimate nutrition automatically</p>
        </div>

        <div
          className={`relative flex flex-1 flex-col items-center justify-center rounded-3xl border-2 border-dashed transition-all duration-300 ${
            recognized
              ? "border-emerald-500/40 bg-emerald-500/[0.03]"
              : "border-zinc-800 bg-zinc-900/30"
          } min-h-[340px] p-8 text-center`}
        >
          <div
            className={`mb-5 flex h-16 w-16 items-center justify-center rounded-2xl transition-colors duration-300 ${
              recognized ? "bg-emerald-500/10" : "bg-zinc-800/60"
            }`}
          >
            <Camera
              className={`h-8 w-8 transition-colors duration-300 ${
                recognized ? "text-emerald-400" : "text-zinc-500"
              }`}
            />
          </div>
          <p className="text-balance text-sm font-medium text-zinc-300">
            {recognized
              ? "Recognition complete · Detected: Chicken Breast + Brown Rice + Broccoli"
              : "Camera Feed (Waiting for YOLO stream)"}
          </p>
          <p className="mt-1.5 text-xs text-zinc-600">
            {recognized ? "The panel on the right has been updated with this meal" : "Waiting for YOLO stream"}
          </p>
        </div>

        <button
          onClick={() => setRecognized(true)}
          className="group flex items-center justify-center gap-2 self-center rounded-xl bg-blue-600 px-8 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition-all duration-200 hover:bg-blue-500 hover:shadow-blue-500/30 active:scale-[0.98]"
        >
          <Camera className="h-4 w-4" />
          Capture / Upload Image
        </button>
      </section>

      {/* Right data panel */}
      <aside className="flex w-full shrink-0 flex-col gap-5 border-t border-zinc-900 p-5 lg:w-80 lg:border-t-0 lg:border-l lg:overflow-y-auto">
        <div className="flex flex-col items-center rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 text-center">
          <span className="text-xs uppercase tracking-wider text-zinc-500">Detected Calories</span>
          <span className="mt-1 text-4xl font-bold tracking-tight text-orange-400">
            320 <span className="text-lg font-medium text-orange-400/70">kcal</span>
          </span>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5">
          <MacroDonut data={donutData} centerLabel="340g" centerSub="Current Meal" />

          <div className="mt-5 flex flex-col gap-4">
            {MACROS.map((m) => (
              <MacroBar key={m.key} name={m.name} grams={m.grams} goal={m.goal} color={m.color} />
            ))}
          </div>
        </div>

        <div className="flex items-start gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4">
          <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
            <Info className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-xs leading-relaxed text-zinc-400">
            <span className="font-semibold text-zinc-200">System Advice: </span>
            Good protein intake. The current meal perfectly aligns with your fat loss requirements.
          </p>
        </div>

        <button className="group mt-auto flex items-center justify-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900/60 px-6 py-3 text-sm font-medium text-zinc-200 transition-all duration-200 hover:border-emerald-500/40 hover:bg-emerald-500/5 hover:text-emerald-300 active:scale-[0.98]">
          <CircleCheck className="h-4 w-4" />
          Confirm Intake
        </button>
        <p className="-mt-2 text-center text-[11px] leading-relaxed text-zinc-600">
          Data will be logged to the diet notes database for daily tracking
        </p>
      </aside>
    </div>
  )
}
