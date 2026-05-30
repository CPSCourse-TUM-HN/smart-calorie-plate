"use client"

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts"

export type Macro = {
  name: string
  value: number
  color: string
}

export function MacroDonut({
  data,
  centerLabel,
  centerSub,
}: {
  data: Macro[]
  centerLabel: string
  centerSub: string
}) {
  return (
    <div className="relative mx-auto h-52 w-52">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={62}
            outerRadius={88}
            paddingAngle={3}
            cornerRadius={8}
            stroke="none"
            startAngle={90}
            endAngle={-270}
            isAnimationActive
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold tracking-tight text-zinc-50">{centerLabel}</span>
        <span className="mt-0.5 text-xs font-medium uppercase tracking-widest text-zinc-500">{centerSub}</span>
      </div>
    </div>
  )
}
