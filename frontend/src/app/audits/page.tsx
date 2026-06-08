"use client"

import * as React from "react"
import Link from "next/link"
import { Clock, FileText } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API_KEY = "pa_dev_key"

interface AuditRun {
  id: string
  claim_number: string | null
  vehicle_year: number | null
  vehicle_make: string | null
  vehicle_model: string | null
  insurance_company: string | null
  status: string
  findings_count: number
  passed_count: number
  failed_count: number
  created_at: string
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
}

export default function AuditsPage() {
  const [audits, setAudits] = React.useState<AuditRun[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState("")

  React.useEffect(() => {
    fetch(`${API_URL}/api/audits`, { headers: { "X-API-Key": API_KEY } })
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then((data) => {
        setAudits(data.audits || data || [])
        setLoading(false)
      })
      .catch((err) => {
        setError(typeof err === "number" ? `HTTP ${err}` : err.message || "Failed to load")
        setLoading(false)
      })
  }, [])

  if (loading) return <div className="p-6 text-sm text-[#8b949e]">Loading...</div>
  if (error) return <div className="p-6 text-sm text-red-400">Error: {error}</div>

  return (
    <div className="p-6">
      <h2 className="mb-4 text-lg font-semibold text-[#c9d1d9]">Audit Runs</h2>
      {audits.length === 0 ? (
        <p className="text-sm text-[#8b949e]">No audits yet.</p>
      ) : (
        <div className="space-y-2">
          {audits.map((a) => {
            const vehicle = [a.vehicle_year, a.vehicle_make, a.vehicle_model].filter(Boolean).join(" ") || "Unknown vehicle"
            return (
              <Link
                key={a.id}
                href={`/audit/${a.id}`}
                className="flex items-center justify-between rounded-lg border border-[#21262d] bg-[#161b22] p-4 hover:border-[#30363d]"
              >
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-[#484f58]" />
                  <div>
                    <p className="text-sm font-medium text-[#c9d1d9]">
                      {a.claim_number || "Untitled Audit"}
                    </p>
                    <p className="text-xs text-[#8b949e]">{vehicle} — {a.insurance_company || "No insurer"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-[#8b949e]">
                      {a.findings_count} findings
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[#484f58]">
                    <Clock className="h-3.5 w-3.5" />
                    <span className="text-xs">{formatDate(a.created_at)}</span>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
