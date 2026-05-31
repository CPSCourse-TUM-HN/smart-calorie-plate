"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import {
  Camera,
  CircleCheck,
  Flame,
  Info,
  LayoutDashboard,
  Loader2,
  LogOut,
  NotebookPen,
  RefreshCw,
  Settings,
  Trash2,
  Upload,
  UtensilsCrossed,
  Users,
  Zap,
} from "lucide-react"
import { MacroDonut } from "@/components/macro-donut"
import type { Profile } from "@/components/setup-screen"
import {
  analyzeByIds,
  createMeal,
  deleteUserProfile,
  detectMeal,
  getDaySummary,
  getRecommendation,
  listMeals,
  listUserProfiles,
  type AnalyzeResult,
  type DaySummary,
  type Detection,
  type MealRecord,
  type Recommendation,
  type UserProfileRecord,
} from "@/lib/api"

const DIET_LABELS: Record<string, string> = {
  fatloss: "Fat Loss Phase",
  maintain: "Maintenance Phase",
  bulk: "Bulking Phase",
  fat_loss: "Fat Loss Phase",
  balance: "Maintenance Phase",
  muscle_gain: "Bulking Phase",
}

type Tab = "dashboard" | "notes" | "analysis" | "account"

type DraftItem = Detection & { weight_g: number }

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
  const pct = goal > 0 ? Math.min(100, Math.round((grams / goal) * 100)) : 0
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-2 font-medium text-zinc-300">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
          {name}
        </span>
        <span className="tabular-nums text-zinc-400">
          {Math.round(grams)}g <span className="text-zinc-600">/ {Math.round(goal)}g</span>
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
  onClick,
}: {
  icon: typeof LayoutDashboard
  label: string
  active?: boolean
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all duration-200 ${
        active
          ? "bg-zinc-800/80 text-zinc-50"
          : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
      }`}
    >
      <Icon className="h-4.5 w-4.5" />
      {label}
    </button>
  )
}

export function Dashboard({ profile, onReset }: { profile: Profile; onReset: () => void }) {
  const targets = profile.targets

  const [tab, setTab] = useState<Tab>("dashboard")
  const [userId, setUserId] = useState<number | null>(profile.userId)
  const [toast, setToast] = useState<string | null>(null)

  // 图片识别工作台
  const [preview, setPreview] = useState<string | null>(null)
  const [detecting, setDetecting] = useState(false)
  const [draft, setDraft] = useState<DraftItem[]>([])
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [cameraOn, setCameraOn] = useState(false)

  // 数据记忆 / 汇总 / 推荐
  const [summary, setSummary] = useState<DaySummary | null>(null)
  const [history, setHistory] = useState<MealRecord[]>([])
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [profiles, setProfiles] = useState<UserProfileRecord[]>([])

  const fileRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const dietLabel = DIET_LABELS[profile.diet] ?? "Fat Loss Phase"

  const flash = useCallback((msg: string) => {
    setToast(msg)
    window.setTimeout(() => setToast(null), 3200)
  }, [])

  const refreshSummary = useCallback(async () => {
    try {
      setSummary(await getDaySummary(userId))
    } catch {
      /* 离线则忽略，保持页面可用 */
    }
  }, [userId])

  const refreshHistory = useCallback(async () => {
    try {
      setHistory(await listMeals(userId))
    } catch {
      /* ignore */
    }
  }, [userId])

  useEffect(() => {
    refreshSummary()
    refreshHistory()
  }, [refreshSummary, refreshHistory])

  // ----- 图片处理 -----
  const handleFile = useCallback(
    async (file: File) => {
      setAnalysis(null)
      setDraft([])
      setPreview(URL.createObjectURL(file))
      setDetecting(true)
      try {
        const { detections } = await detectMeal(file)
        if (detections.length === 0) {
          flash("No known foods detected. Try a clearer photo or a lower confidence threshold.")
        }
        setDraft(detections.map((d) => ({ ...d, weight_g: 100 })))
      } catch (e) {
        flash(e instanceof Error ? e.message : "Detection failed")
      } finally {
        setDetecting(false)
      }
    },
    [flash],
  )

  const onPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ""
  }

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
      streamRef.current = stream
      setCameraOn(true)
      // 等 video 元素渲染后再绑定流
      window.setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          videoRef.current.play().catch(() => {})
        }
      }, 50)
    } catch (e) {
      flash("Cannot access camera (YOLO device / webcam): " + (e instanceof Error ? e.message : ""))
    }
  }

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    setCameraOn(false)
  }, [])

  const captureFrame = () => {
    const video = videoRef.current
    if (!video) return
    const canvas = document.createElement("canvas")
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext("2d")?.drawImage(video, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (!blob) return
        stopCamera()
        handleFile(new File([blob], "capture.jpg", { type: "image/jpeg" }))
      },
      "image/jpeg",
      0.92,
    )
  }

  useEffect(() => () => stopCamera(), [stopCamera])

  const setWeight = (idx: number, value: string) =>
    setDraft((prev) => prev.map((it, i) => (i === idx ? { ...it, weight_g: Number(value) || 0 } : it)))

  const runAnalyze = async () => {
    if (draft.length === 0) return
    setAnalyzing(true)
    try {
      const res = await analyzeByIds(draft.map((d) => ({ food_id: d.food_id, weight_g: d.weight_g })))
      setAnalysis(res)
    } catch (e) {
      flash(e instanceof Error ? e.message : "Analysis failed")
    } finally {
      setAnalyzing(false)
    }
  }

  const confirmIntake = async () => {
    if (!analysis) return
    setConfirming(true)
    try {
      await createMeal({
        user_id: userId,
        total_kcal: analysis.total_kcal,
        total_protein_g: analysis.total_protein,
        total_carbs_g: analysis.total_carbs,
        total_fat_g: analysis.total_fat,
        items: analysis.items,
        advice: analysis.advice.join(" "),
      })
      flash("Saved to diet notes ✓")
      setAnalysis(null)
      setDraft([])
      setPreview(null)
      await Promise.all([refreshSummary(), refreshHistory()])
    } catch (e) {
      flash(e instanceof Error ? e.message : "Save failed (make sure the backend is running)")
    } finally {
      setConfirming(false)
    }
  }

  const loadRecommendation = useCallback(async () => {
    try {
      const rec = await getRecommendation({
        target_calories: targets.target_calories,
        target_protein_g: targets.target_protein_g,
        target_carbs_g: targets.target_carbs_g,
        target_fat_g: targets.target_fat_g,
        actual_calories: summary?.total_kcal ?? 0,
        actual_protein_g: summary?.total_protein_g ?? 0,
        actual_carbs_g: summary?.total_carbs_g ?? 0,
        actual_fat_g: summary?.total_fat_g ?? 0,
      })
      setRecommendation(rec)
    } catch (e) {
      flash(e instanceof Error ? e.message : "Failed to load recommendation")
    }
  }, [targets, summary, flash])

  const loadProfiles = useCallback(async () => {
    try {
      setProfiles(await listUserProfiles())
    } catch {
      /* ignore */
    }
  }, [])

  const deleteProfile = useCallback(
    async (id: number) => {
      try {
        await deleteUserProfile(id)
        setProfiles((prev) => prev.filter((p) => p.id !== id))
        flash(`Deleted account #${id}`)
        // 删掉的是当前账号 → 回到设置页重新建档。
        if (id === userId) onReset()
      } catch (e) {
        flash(e instanceof Error ? e.message : "Delete failed")
      }
    },
    [userId, onReset, flash],
  )

  const goTab = (next: Tab) => {
    setTab(next)
    if (next === "analysis") loadRecommendation()
    if (next === "account") loadProfiles()
    if (next === "notes") refreshHistory()
  }

  // 右侧面板用：当日已摄入 vs 目标
  const consumed = {
    kcal: summary?.total_kcal ?? 0,
    protein: summary?.total_protein_g ?? 0,
    carbs: summary?.total_carbs_g ?? 0,
    fat: summary?.total_fat_g ?? 0,
  }
  const donutData = [
    { name: "Carbs", value: Math.max(consumed.carbs, 0.001), color: "#3b82f6" },
    { name: "Protein", value: Math.max(consumed.protein, 0.001), color: "#ec4899" },
    { name: "Fat", value: Math.max(consumed.fat, 0.001), color: "#eab308" },
  ]

  return (
    <div className="flex min-h-screen flex-col bg-zinc-950 text-zinc-100 lg:h-screen lg:flex-row lg:overflow-hidden">
      {/* ===== Left sidebar ===== */}
      <aside className="flex w-full shrink-0 flex-col gap-6 border-b border-zinc-900 p-5 lg:w-72 lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-2.5 px-1.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600 shadow-lg shadow-emerald-600/30">
            <UtensilsCrossed className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-zinc-50">Smart Plate</span>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="max-w-[60%] truncate text-sm font-semibold text-zinc-100">
              {profile.name || (userId ? `User #${userId}` : "Guest")}
            </span>
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400">
              {dietLabel}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-3 rounded-xl bg-zinc-950/60 p-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-500/10">
              <Flame className="h-4.5 w-4.5 text-orange-400" />
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] uppercase tracking-wider text-zinc-400">Daily Goal</span>
              <span className="text-base font-bold tabular-nums text-zinc-50">
                {Math.round(targets.target_calories)}{" "}
                <span className="text-xs font-normal text-zinc-400">kcal</span>
              </span>
            </div>
          </div>
        </div>

        <nav className="flex flex-col gap-1">
          <NavItem icon={LayoutDashboard} label="Dashboard" active={tab === "dashboard"} onClick={() => goTab("dashboard")} />
          <NavItem icon={NotebookPen} label="Diet Notes" active={tab === "notes"} onClick={() => goTab("notes")} />
          <NavItem icon={Zap} label="Nutrition Analysis" active={tab === "analysis"} onClick={() => goTab("analysis")} />
          <NavItem icon={Settings} label="Account Settings" active={tab === "account"} onClick={() => goTab("account")} />
        </nav>

        <button
          onClick={onReset}
          className="mt-auto flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium text-zinc-400 transition-all duration-200 hover:bg-zinc-900 hover:text-zinc-200"
        >
          <LogOut className="h-4.5 w-4.5" />
          Log Out / Reset
        </button>
      </aside>

      {/* ===== Center main view ===== */}
      <section className="flex flex-1 flex-col gap-5 p-5 lg:overflow-y-auto lg:p-8">
        {tab === "dashboard" && (
          <DashboardTab
            preview={preview}
            detecting={detecting}
            draft={draft}
            analysis={analysis}
            analyzing={analyzing}
            cameraOn={cameraOn}
            videoRef={videoRef}
            fileRef={fileRef}
            onPick={onPick}
            onStartCamera={startCamera}
            onStopCamera={stopCamera}
            onCapture={captureFrame}
            onWeight={setWeight}
            onAnalyze={runAnalyze}
          />
        )}

        {tab === "notes" && <NotesTab history={history} onRefresh={refreshHistory} />}

        {tab === "analysis" && (
          <AnalysisTab recommendation={recommendation} onRefresh={loadRecommendation} />
        )}

        {tab === "account" && (
          <AccountTab
            profiles={profiles}
            currentId={userId}
            onSwitch={(id) => {
              setUserId(id)
              flash(`Switched to account #${id}`)
            }}
            onDelete={deleteProfile}
            onRefresh={loadProfiles}
            onReset={onReset}
          />
        )}
      </section>

      {/* ===== Right data panel (always: today's progress) ===== */}
      <aside className="flex w-full shrink-0 flex-col gap-5 border-t border-zinc-900 p-5 lg:w-80 lg:border-t-0 lg:border-l lg:overflow-y-auto">
        <div className="flex flex-col items-center rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 text-center">
          <span className="text-xs uppercase tracking-wider text-zinc-400">
            {analysis ? "This Meal" : "Today's Calories"}
          </span>
          <span className="mt-1 text-4xl font-bold tracking-tight text-orange-400">
            {Math.round(analysis ? analysis.total_kcal : consumed.kcal)}{" "}
            <span className="text-lg font-medium text-orange-400/70">kcal</span>
          </span>
          {!analysis && (
            <span className="mt-1 text-xs text-zinc-400">
              Goal {Math.round(targets.target_calories)} kcal · {summary?.meal_count ?? 0} meals
            </span>
          )}
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5">
          <MacroDonut
            data={donutData}
            centerLabel={`${Math.round(consumed.carbs + consumed.protein + consumed.fat)}g`}
            centerSub="Today Intake"
          />
          <div className="mt-5 flex flex-col gap-4">
            <MacroBar name="Carbs" grams={consumed.carbs} goal={targets.target_carbs_g} color="#3b82f6" />
            <MacroBar name="Protein" grams={consumed.protein} goal={targets.target_protein_g} color="#ec4899" />
            <MacroBar name="Fat" grams={consumed.fat} goal={targets.target_fat_g} color="#eab308" />
          </div>
        </div>

        {analysis && (
          <div className="flex items-start gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
              <Info className="h-4 w-4 text-emerald-400" />
            </div>
            <p className="text-xs leading-relaxed text-zinc-400">
              <span className="font-semibold text-zinc-200">System Advice: </span>
              {analysis.advice.join(" ")}
            </p>
          </div>
        )}

        {analysis && (
          <>
            <button
              onClick={confirmIntake}
              disabled={confirming}
              className="group mt-auto flex items-center justify-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900/60 px-6 py-3 text-sm font-medium text-zinc-200 transition-all duration-200 hover:border-emerald-500/40 hover:bg-emerald-500/5 hover:text-emerald-300 active:scale-[0.98] disabled:opacity-60"
            >
              {confirming ? <Loader2 className="h-4 w-4 animate-spin" /> : <CircleCheck className="h-4 w-4" />}
              Confirm Intake
            </button>
            <p className="-mt-2 text-center text-[11px] leading-relaxed text-zinc-500">
              Data will be logged to the diet notes database for daily tracking
            </p>
          </>
        )}
      </aside>

      {/* toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm text-zinc-100 shadow-2xl shadow-black/60">
          {toast}
        </div>
      )}
    </div>
  )
}

/* ===================== Tab: Dashboard (image workbench) ===================== */
function DashboardTab(props: {
  preview: string | null
  detecting: boolean
  draft: DraftItem[]
  analysis: AnalyzeResult | null
  analyzing: boolean
  cameraOn: boolean
  videoRef: React.RefObject<HTMLVideoElement | null>
  fileRef: React.RefObject<HTMLInputElement | null>
  onPick: (e: React.ChangeEvent<HTMLInputElement>) => void
  onStartCamera: () => void
  onStopCamera: () => void
  onCapture: () => void
  onWeight: (idx: number, value: string) => void
  onAnalyze: () => void
}) {
  const {
    preview, detecting, draft, analysis, analyzing, cameraOn,
    videoRef, fileRef, onPick, onStartCamera, onStopCamera, onCapture, onWeight, onAnalyze,
  } = props
  const recognized = draft.length > 0 || !!analysis

  return (
    <>
      <div>
        <h2 className="text-xl font-bold tracking-tight text-zinc-50">Image Recognition Workbench</h2>
        <p className="mt-1 text-sm text-zinc-400">
          Upload a plate photo or connect a camera. YOLO detects foods and estimates nutrition automatically.
        </p>
      </div>

      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onPick} />

      <div
        className={`relative flex flex-1 flex-col items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed transition-all duration-300 ${
          recognized ? "border-emerald-500/40 bg-emerald-500/[0.03]" : "border-zinc-800 bg-zinc-900/30"
        } min-h-[300px] p-6 text-center`}
      >
        {cameraOn ? (
          <video ref={videoRef} playsInline muted className="max-h-[360px] w-auto rounded-2xl" />
        ) : preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt="preview" className="max-h-[360px] w-auto rounded-2xl object-contain" />
        ) : (
          <>
            <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800/60">
              <Camera className="h-8 w-8 text-zinc-400" />
            </div>
            <p className="text-balance text-sm font-medium text-zinc-300">
              Click below to upload an image, or turn on the camera to capture live
            </p>
            <p className="mt-1.5 text-xs text-zinc-500">Waiting for image / YOLO stream</p>
          </>
        )}

        {detecting && (
          <div className="absolute inset-0 flex items-center justify-center bg-zinc-950/60 backdrop-blur-sm">
            <span className="flex items-center gap-2 text-sm text-emerald-300">
              <Loader2 className="h-4 w-4 animate-spin" /> Detecting with YOLO…
            </span>
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={() => fileRef.current?.click()}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition-all hover:bg-blue-500 active:scale-[0.98]"
        >
          <Upload className="h-4 w-4" /> Upload Image
        </button>
        {cameraOn ? (
          <>
            <button
              onClick={onCapture}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-600/20 transition-all hover:bg-emerald-500 active:scale-[0.98]"
            >
              <Camera className="h-4 w-4" /> Capture
            </button>
            <button
              onClick={onStopCamera}
              className="rounded-xl border border-zinc-800 px-4 py-3 text-sm font-medium text-zinc-400 hover:bg-zinc-900"
            >
              Stop
            </button>
          </>
        ) : (
          <button
            onClick={onStartCamera}
            className="flex items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900/60 px-6 py-3 text-sm font-medium text-zinc-200 transition-all hover:border-emerald-500/40 hover:text-emerald-300 active:scale-[0.98]"
          >
            <Camera className="h-4 w-4" /> Use Camera
          </button>
        )}
      </div>

      {/* 检测结果 + 重量编辑 */}
      {draft.length > 0 && (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5">
          <h3 className="mb-3 text-sm font-semibold text-zinc-100">
            Detected Foods · enter the weight of each item (g)
          </h3>
          <div className="flex flex-col gap-2.5">
            {draft.map((d, i) => (
              <div key={i} className="flex items-center gap-3 rounded-xl bg-zinc-950/50 px-3 py-2.5">
                <div className="flex-1">
                  <span className="text-sm font-medium capitalize text-zinc-100">
                    {d.name_en}
                  </span>
                  <span className="ml-2 text-xs text-zinc-400">
                    {(d.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="number"
                  min={0}
                  value={d.weight_g}
                  onChange={(e) => onWeight(i, e.target.value)}
                  className="h-9 w-24 rounded-lg border border-zinc-800 bg-zinc-900 px-3 text-sm text-zinc-100 outline-none focus:border-emerald-500/60"
                />
                <span className="text-xs text-zinc-400">g</span>
              </div>
            ))}
          </div>
          <button
            onClick={onAnalyze}
            disabled={analyzing}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-600/20 transition-all hover:bg-emerald-500 active:scale-[0.98] disabled:opacity-60"
          >
            {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            Analyze Nutrition
          </button>
        </div>
      )}

      {/* 计算结果明细 */}
      {analysis && (
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.03] p-5">
          <h3 className="mb-3 text-sm font-semibold text-emerald-300">Nutrition Breakdown · This Meal</h3>
          <div className="overflow-hidden rounded-xl border border-zinc-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-900/70 text-zinc-400">
                <tr>
                  <th className="px-3 py-2 font-medium">Food</th>
                  <th className="px-3 py-2 text-right font-medium">Weight</th>
                  <th className="px-3 py-2 text-right font-medium">kcal</th>
                  <th className="px-3 py-2 text-right font-medium">Protein</th>
                  <th className="px-3 py-2 text-right font-medium">Carbs</th>
                  <th className="px-3 py-2 text-right font-medium">Fat</th>
                </tr>
              </thead>
              <tbody className="text-zinc-200">
                {analysis.items.map((it, i) => (
                  <tr key={i} className="border-t border-zinc-800/70">
                    <td className="px-3 py-2 capitalize">{it.name_en}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{it.weight_g}g</td>
                    <td className="px-3 py-2 text-right tabular-nums">{it.kcal}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{it.protein}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{it.carbs}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{it.fat}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-zinc-400">
            Total {analysis.total_kcal} kcal · confirm on the right to log it to today&apos;s diet notes.
          </p>
        </div>
      )}
    </>
  )
}

/* ===================== Tab: Diet Notes (history / 数据记忆) ===================== */
function NotesTab({ history, onRefresh }: { history: MealRecord[]; onRefresh: () => void }) {
  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-zinc-50">Diet Notes</h2>
          <p className="mt-1 text-sm text-zinc-400">Meal history (persistent memory)</p>
        </div>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 rounded-xl border border-zinc-800 px-3.5 py-2 text-sm text-zinc-300 hover:bg-zinc-900"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {history.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center rounded-3xl border-2 border-dashed border-zinc-800 p-10 text-center text-sm text-zinc-400">
          <NotebookPen className="mb-3 h-8 w-8 text-zinc-600" />
          No records yet. Go to the Dashboard, upload a plate photo, and confirm your intake.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {history.map((m) => (
            <div key={m.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-zinc-100">
                  {new Date(m.created_at).toLocaleString()}
                </span>
                <span className="text-sm font-bold tabular-nums text-orange-400">{m.total_kcal} kcal</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {m.items.map((it, i) => (
                  <span key={i} className="rounded-full bg-zinc-800/70 px-2.5 py-0.5 text-[11px] capitalize text-zinc-300">
                    {it.name_en} {it.weight_g}g
                  </span>
                ))}
              </div>
              <div className="mt-2 flex gap-4 text-[11px] text-zinc-400">
                <span>Protein {m.total_protein_g}g</span>
                <span>Carbs {m.total_carbs_g}g</span>
                <span>Fat {m.total_fat_g}g</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

/* ===================== Tab: Nutrition Analysis (推荐) ===================== */
function AnalysisTab({
  recommendation,
  onRefresh,
}: {
  recommendation: Recommendation | null
  onRefresh: () => void
}) {
  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-zinc-50">Nutrition Analysis</h2>
          <p className="mt-1 text-sm text-zinc-400">Smart recommendations based on today&apos;s intake vs. goals</p>
        </div>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 rounded-xl border border-zinc-800 px-3.5 py-2 text-sm text-zinc-300 hover:bg-zinc-900"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {!recommendation ? (
        <div className="flex flex-1 items-center justify-center text-sm text-zinc-400">Loading recommendations…</div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Calories Left", value: `${Math.round(recommendation.remaining.calories)} kcal` },
              { label: "Protein Left", value: `${Math.round(recommendation.remaining.protein_g)} g` },
              { label: "Carbs Left", value: `${Math.round(recommendation.remaining.carbs_g)} g` },
              { label: "Fat Left", value: `${Math.round(recommendation.remaining.fat_g)} g` },
            ].map((c) => (
              <div key={c.label} className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4 text-center">
                <div className="text-[11px] uppercase tracking-wider text-zinc-400">{c.label}</div>
                <div className="mt-1 text-lg font-bold tabular-nums text-zinc-50">{c.value}</div>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h3 className="mb-2 text-sm font-semibold text-zinc-100">Recommendations</h3>
            <ul className="flex flex-col gap-1.5 text-sm text-zinc-300">
              {recommendation.tips.map((t, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                  {t}
                </li>
              ))}
            </ul>
          </div>

          {recommendation.suggested_foods.length > 0 && (
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5">
              <h3 className="mb-3 text-sm font-semibold text-zinc-100">Suggested Foods</h3>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {recommendation.suggested_foods.map((f) => (
                  <div key={f.food_id} className="rounded-xl bg-zinc-950/50 p-3 text-center">
                    <div className="text-sm font-medium capitalize text-zinc-100">{f.name_en}</div>
                    <div className="mt-1 text-[11px] text-zinc-400">
                      {f.kcal_per_100g} kcal · {f.protein_per_100g}g protein /100g
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </>
  )
}

/* ===================== Tab: Account Settings (账号切换) ===================== */
function AccountTab({
  profiles,
  currentId,
  onSwitch,
  onDelete,
  onRefresh,
  onReset,
}: {
  profiles: UserProfileRecord[]
  currentId: number | null
  onSwitch: (id: number) => void
  onDelete: (id: number) => void
  onRefresh: () => void
  onReset: () => void
}) {
  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-zinc-50">Account Settings</h2>
          <p className="mt-1 text-sm text-zinc-400">Switch account or create a new body profile</p>
        </div>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 rounded-xl border border-zinc-800 px-3.5 py-2 text-sm text-zinc-300 hover:bg-zinc-900"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {profiles.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center rounded-3xl border-2 border-dashed border-zinc-800 p-10 text-center text-sm text-zinc-400">
          <Users className="mb-3 h-8 w-8 text-zinc-600" />
          No saved accounts yet (backend not connected, or none created).
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {profiles.map((p) => {
            const active = p.id === currentId
            return (
              <div
                key={p.id}
                className={`flex items-center justify-between rounded-2xl border p-4 ${
                  active ? "border-emerald-500/40 bg-emerald-500/[0.04]" : "border-zinc-800 bg-zinc-900/40"
                }`}
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-zinc-100">
                    {p.name || `User #${p.id}`}{" "}
                    {active && <span className="text-emerald-400">· current</span>}
                  </div>
                  <div className="mt-0.5 text-[11px] text-zinc-400">
                    {p.gender}, {p.age}y · {p.height_cm}cm / {p.weight_kg}kg · {Math.round(p.target_calories ?? 0)} kcal
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {!active && (
                    <button
                      onClick={() => onSwitch(p.id)}
                      className="rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-emerald-500"
                    >
                      Switch
                    </button>
                  )}
                  <button
                    onClick={() => onDelete(p.id)}
                    title="Delete account"
                    aria-label="Delete account"
                    className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 text-zinc-400 transition-colors hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <button
        onClick={onReset}
        className="mt-2 flex items-center justify-center gap-2 self-start rounded-xl border border-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-300 hover:bg-zinc-900"
      >
        <Trash2 className="h-4 w-4" /> New Profile / Back to Setup
      </button>
    </>
  )
}
