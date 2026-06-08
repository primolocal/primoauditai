"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, AlertTriangle, CheckCircle, HelpCircle, Ban, X } from "lucide-react"

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
  override_reason: string | null
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

async function patchFinding(auditId: string, findingId: string, body: object) {
  const res = await fetch(`${API_URL}/api/audits/${auditId}/findings/${findingId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export default function AuditDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [audit, setAudit] = React.useState<AuditRun | null>(null)
  const [findings, setFindings] = React.useState<Finding[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState("")
  const [editingId, setEditingId] = React.useState<string | null>(null)
  const [reasonInput, setReasonInput] = React.useState("")
  const [savingId, setSavingId] = React.useState<string | null>(null)

  const id = params.id

  const load = React.useCallback(() => {
    setLoading(true)
    Promise.all([
      fetch(`${API_URL}/api/audits/${id}`, { headers: { "X-API-Key": API_KEY } }).then(r => r.ok ? r.json() : Promise.reject(r.status)),
      fetch(`${API_URL}/api/audits/${id}/findings`, { headers: { "X-API-Key": API_KEY } }).then(r => r.ok ? r.json() : Promise.reject(r.status)),
    ])
    .then(([a, f]) => {
      setAudit(a)
      setFindings(Array.isArray(f) ? f : (f.items || f.findings || []))
      setLoading(false)
    })
    .catch((err) => {
      setError(typeof err === "number" ? `HTTP ${err}` : err.message || "Failed to load")
      setLoading(false)
    })
  }, [id])

  React.useEffect(() => { load() }, [load])

  async function handleConfirm(findingId: string) {
    setSavingId(findingId)
    try {
      await patchFinding(id, findingId, { status: "confirmed" })
      setFindings(prev => prev.map(f => f.id === findingId ? { ...f, status: "confirmed" } : f))
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSavingId(null)
    }
  }

  async function handleOverride(findingId: string) {
    setSavingId(findingId)
    try {
      await patchFinding(id, findingId, { status: "override", applies: false })
      setFindings(prev => prev.map(f => f.id === findingId ? { ...f, status: "override", applies: false } : f))
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSavingId(null)
    }
  }

  async function handleSaveReason(findingId: string) {
    if (!reasonInput.trim()) return
    setSavingId(findingId)
    try {
      await patchFinding(id, findingId, { override_reason: reasonInput.trim() })
      setFindings(prev => prev.map(f => f.id === findingId ? { ...f, override_reason: reasonInput.trim() } : f))
      setEditingId(null)
      setReasonInput("")
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSavingId(null)
    }
  }

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
            <div key={f.id} className={`rounded-lg border bg-[#161b22] p-3 hover:border-[#30363d] ${f.status === "override" ? "border-purple-500/30" : f.status === "confirmed" ? "border-green-500/30" : "border-[#21262d]"}`}>
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
              <p className="mb-2 text-sm text-[#c9d1d9]">{f.description}</p>

              {/* Action row */}
              <div className="flex items-center gap-2">
                {f.status !== "confirmed" && (
                  <button
                    onClick={() => handleConfirm(f.id)}
                    disabled={savingId === f.id}
                    className="inline-flex items-center gap-1 rounded border border-green-500/30 bg-green-500/10 px-2 py-1 text-xs text-green-400 hover:bg-green-500/20 disabled:opacity-50"
                  >
                    <CheckCircle className="h-3 w-3" />
                    Confirm
                  </button>
                )}
                {f.status !== "override" && (
                  <button
                    onClick={() => handleOverride(f.id)}
                    disabled={savingId === f.id}
                    className="inline-flex items-center gap-1 rounded border border-purple-500/30 bg-purple-500/10 px-2 py-1 text-xs text-purple-400 hover:bg-purple-500/20 disabled:opacity-50"
                  >
                    <Ban className="h-3 w-3" />
                    Override
                  </button>
                )}
                {editingId === f.id ? (
                  <div className="flex items-center gap-1">
                    <input
                      autoFocus
                      className="rounded border border-[#30363d] bg-[#0d1117] px-2 py-1 text-xs text-[#c9d1d9] placeholder-[#484f58] outline-none focus:border-[#58a6ff]"
                      placeholder="Reason..."
                      value={reasonInput}
                      onChange={(e) => setReasonInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") handleSaveReason(f.id) }}
                    />
                    <button
                      onClick={() => handleSaveReason(f.id)}
                      disabled={savingId === f.id || !reasonInput.trim()}
                      className="rounded border border-[#30363d] px-2 py-1 text-xs text-[#c9d1d9] hover:bg-[#21262d] disabled:opacity-50"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => { setEditingId(null); setReasonInput("") }}
                      className="rounded px-1 py-1 text-xs text-[#8b949e] hover:text-[#c9d1d9]"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => { setEditingId(f.id); setReasonInput(f.override_reason || "") }}
                    className="text-xs text-[#8b949e] hover:text-[#c9d1d9]"
                  >
                    {f.override_reason ? "Edit reason" : "Add reason"}
                  </button>
                )}
              </div>

              {f.override_reason && (
                <p className="mt-1 text-xs text-[#8b949e]">
                  Reason: {f.override_reason}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
