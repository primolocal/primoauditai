"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, AlertTriangle, CheckCircle, HelpCircle, Ban } from "lucide-react"

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

interface Finding {
  id: string
  rule_id: string
  category: string
  severity: string
  description: string
  line_numbers: number[]
  confidence: number
  applies: boolean
  status: string
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-500/20 text-red-400",
    high: "bg-orange-500/20 text-orange-400",
    medium: "bg-yellow-500/20 text-yellow-400",
    low: "bg-blue-500/20 text-blue-400",
  }
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${colors[severity] || colors.low}`}>
      {severity}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; icon: React.ReactNode }> = {
    confirmed: { color: "text-green-400", icon: <CheckCircle className="h-3 w-3" /> },
    questionable: { color: "text-yellow-400", icon: <HelpCircle className="h-3 w-3" /> },
    override: { color: "text-purple-400", icon: <Ban className="h-3 w-3" /> },
    unreviewed: { color: "text-red-400", icon: <AlertTriangle className="h-3 w-3" /> },
  }
  const s = map[status] || map.unreviewed
  return (
    <span className={`inline-flex items-center gap-1 text-xs ${s.color}`}>
      {s.icon}
      {status}
    </span>
  )
}

export default function AuditDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [audit, setAudit] = React.useState<AuditRun | null>(null)
  const [findings, setFindings] = React.useState<Finding[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState("")

  React.useEffect(() => {
    const id = params.id
    Promise.all([
      fetch(`${API_URL}/api/audits/${id}`, { headers: { "X-API-Key": API_KEY } }).then(r => r.ok ? r.json() : Promise.reject(r.status)),
      fetch(`${API_URL}/api/audits/${id}/findings`, { headers: { "X-API-Key": API_KEY } }).then(r => r.ok ? r.json() : Promise.reject(r.status)),
    ])
      .then(([a, f]) => {
        setAudit(a)
        setFindings(f.findings || f || [])
        setLoading(false)
      })
      .catch((err) => {
        setError(typeof err === "number" ? `HTTP ${err}` : err.message || "Failed to load")
        setLoading(false)
      })
  }, [params.id])

  if (loading) return <div className="p-6 text-sm text-[#8b949e]">Loading...</div>
  if (error) return <div className="p-6 text-sm text-red-400">Error: {error}</div>
  if (!audit) return <div className="p-6 text-sm text-[#8b949e]">Not found</div>

  const vehicle = [audit.vehicle_year, audit.vehicle_make, audit.vehicle_model].filter(Boolean).join(" ") || "Unknown vehicle"

  return (
    <div className="p-6">
      <div className="mb-6">
        <button
          onClick={() => router.push("/audits")}
          className="mb-3 flex items-center gap-1 text-sm text-[#8b949e] hover:text-[#c9d1d9]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to audits
        </button>
        <h1 className="text-xl font-semibold text-[#c9d1d9]">{audit.claim_number || "Untitled Audit"}</h1>
        <p className="text-sm text-[#8b949e]">{vehicle}</p>
      </div>

      <div className="mb-6 grid grid-cols-4 gap-3">
        {[
          { label: "Findings", value: audit.findings_count, color: "text-[#f0883e]" },
          { label: "Passed", value: audit.passed_count, color: "text-green-400" },
          { label: "Failed", value: audit.failed_count, color: "text-red-400" },
          { label: "Status", value: audit.status, color: "text-[#c9d1d9]" },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border border-[#21262d] bg-[#161b22] p-3">
            <p className="text-xs text-[#8b949e]">{s.label}</p>
            <p className={`text-lg font-semibold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      <h2 className="mb-3 text-sm font-semibold text-[#c9d1d9]">Findings</h2>
      {findings.length === 0 ? (
        <p className="text-sm text-[#8b949e]">No findings.</p>
      ) : (
        <div className="space-y-2">
          {findings.map((f) => (
            <div key={f.id} className="rounded-lg border border-[#21262d] bg-[#161b22] p-3 hover:border-[#30363d]">
              <div className="mb-1 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-[#484f58]">{f.rule_id}</span>
                  <SeverityBadge severity={f.severity} />
                  <StatusBadge status={f.status} />
                </div>
                <span className="text-xs text-[#484f58]">
                  {f.line_numbers?.length ? `L${f.line_numbers.join(", ")}` : ""}
                </span>
              </div>
              <p className="text-sm text-[#c9d1d9]">{f.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
