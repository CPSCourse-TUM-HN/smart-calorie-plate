"use client"

import { useState } from "react"
import { SetupScreen, type Profile } from "@/components/setup-screen"
import { Dashboard } from "@/components/dashboard"

export default function Page() {
  const [profile, setProfile] = useState<Profile | null>(null)

  if (!profile) {
    return <SetupScreen onSubmit={setProfile} />
  }

  return <Dashboard profile={profile} onReset={() => setProfile(null)} />
}
