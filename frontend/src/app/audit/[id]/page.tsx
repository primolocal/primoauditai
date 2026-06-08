"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, AlertTriangle, CheckCircle, HelpCircle, Ban, X as XIcon } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API_KEY="pa_d...face ParsedLine {
  line_no: string
  is_header?: boolean
  panel_name?: string
  description?: string
  operation?: string
  operation_label?: string
  part_number?: string
  quantity?: number
  part_price?: number
  labor_hours?: number
  paint_hours?: number
  total?: number
  labor_type?: string
  flag?: string
  supplement?: string
  part_type?: string
}

function PartTypeBadge({ part_type }: { part_type?: string }) {
  if (!part_type) return null
  const colors: Record<string, string> = {
    "A/M": "bg-[#8b5cf6]/20 text-[#a78bfa] border-[#8b5cf6]/30",
    "LKQ": "bg-[#f59e0b]/20 text-[#fbbf24] border-[#f59e0b]/30",
    "RECON": "bg-[#10b981]/20 text-[#34d399] border-[#10b981]/30",
    "REC": "bg-[#f59e0b]/20 text-[#fbbf24] border-[#f59e0b]/30",
    "USED": "bg-[#f59e0b]/20 text-[#fbbf24] border-[#f59e0b]/30",
    "OEM": "bg-[#3b82f6]/20 text-[#60a5fa] border-[#3b82f6]/30",
  }
  return (
    <span className={`rounded border px-1.5 py-0 text-[10px] font-semibold ${colors[part_type] || ""}`}>
      {part_type}
    </span>
  )
}

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
  parsed_lines: ParsedLine[] | null
  parsed_panels: Record<string, ParsedLine[]> | null
  parsed_metadata: Record<string, any> | null
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
  const [highlightLine, setHighlightLine] = React.useState<string | null>(null)
  const lineScrollRef = React.useRef<HTMLDivElement>(null)

  const id = params.id

  React.useEffect(() => {
    if (!highlightLine || !lineScrollRef.current) return
    const el = lineScrollRef.current.querySelector(`[data-line="${highlightLine}"]`)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }, [highlightLine])

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
  const lines = audit.parsed_lines || []

  // Build set of line numbers referenced by any finding + their review status
  const referencedLines = new Set<string>()
  const lineStatus = new Map<string, "resolved" | "needs-review">()
  findings.forEach((f) => {
    (f.line_numbers || []).forEach((ln: number) => {
      const s = String(ln)
      referencedLines.add(s)
      if (f.status === "unreviewed" || f.status === "questionable") {
        lineStatus.set(s, "needs-review")
      } else if (!lineStatus.has(s)) {
        // Only set resolved if not already marked needs-review
        lineStatus.set(s, "resolved")
      }
    })
  })

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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 items-start">
        {/* LEFT: Findings */}
        <div>
          <h2 className="mb-3 text-sm font-semibold text-[#c9d1d9]">Findings ({findings.length})</h2>
          {findings.length === 0 ? (
            <p className="text-sm text-[#8b949e]">No findings.</p>
          ) : (
            <div className="space-y-2">
              {findings.map((f) => (
                <div
                  key={f.id}
                  className={`rounded-lg border bg-[#161b22] p-3 hover:border-[#30363d] cursor-pointer ${
                    f.status === "override"
                      ? "border-purple-500/30"
                      : f.status === "confirmed"
                      ? "border-green-500/30"
                      : "border-[#21262d]"
                  }`}
                  onClick={() => {
                    if (f.line_numbers?.length) {
                      setHighlightLine(String(f.line_numbers[0]))
                    }
                  }}
                >
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
                        onClick={(e) => { e.stopPropagation(); handleConfirm(f.id) }}
                        disabled={savingId === f.id}
                        className="inline-flex items-center gap-1 rounded border border-green-500/30 bg-green-500/10 px-2 py-1 text-xs text-green-400 hover:bg-green-500/20 disabled:opacity-50"
                      >
                        <CheckCircle className="h-3 w-3" />
                        Confirm
                      </button>
                    )}
                    {f.status !== "override" && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleOverride(f.id) }}
                        disabled={savingId === f.id}
                        className="inline-flex items-center gap-1 rounded border border-purple-500/30 bg-purple-500/10 px-2 py-1 text-xs text-purple-400 hover:bg-purple-500/20 disabled:opacity-50"
                      >
                        <Ban className="h-3 w-3" />
                        Override
                      </button>
                    )}
                    {editingId === f.id ? (
                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
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
                          <XIcon className="h-3 w-3" />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={(e) => { e.stopPropagation(); setEditingId(f.id); setReasonInput(f.override_reason || "") }}
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

        {/* RIGHT: Estimate Lines */}
        <div className="sticky top-14">
          <h2 className="mb-3 text-sm font-semibold text-[#c9d1d9]">Estimate Lines ({lines.length})</h2>
          <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-2">
            <div className="space-y-0.5 max-h-[70vh] overflow-y-auto" ref={lineScrollRef}>
              {lines.length === 0 ? (
                <p className="px-3 py-4 text-sm text-[#8b949e]">No parsed lines.</p>
              ) : (
                lines.map((line, idx) => {
                  const isHeader = line.is_header
                  const isRef = referencedLines.has(line.line_no)
                  const isHighlight = highlightLine === line.line_no
                  const bg = isHeader
                    ? "bg-[#21262d] font-semibold"
                    : isHighlight
                    ? "bg-[#f0883e]/10"
                    : isRef
                    ? "bg-[#58a6ff]/5"
                    : "hover:bg-[#0d1117]"

                  if (isHeader) {
                    return (
                      <div
                        key={idx}
                        data-line={line.line_no}
                        className={`rounded px-3 py-1.5 text-sm text-[#c9d1d9] ${bg}`}
                      >
                        <span className="text-[#8b949e] mr-2">{line.line_no}</span>
                        {line.panel_name || line.description || ""}
                      </div>
                    )
                  }

                  return (
                    <div
                      key={idx}
                      data-line={line.line_no}
                      className={`flex items-start gap-3 rounded px-3 py-1.5 text-xs transition-colors cursor-pointer ${bg} ${isHighlight ? "border-l-2 border-l-[#f0883e]" : ""}`}
                      onClick={() => setHighlightLine(line.line_no === highlightLine ? null : line.line_no)}
                    >
                      <span className={`font-mono min-w-[2ch] text-right shrink-0 ${isRef ? "text-[#58a6ff] font-semibold" : "text-[#484f58]"}`}>
                        {line.line_no}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          {line.flag && <span className="text-[#f0883e] font-bold">{line.flag}</span>}
                          {line.operation && (
                            <span className="rounded bg-[#21262d] px-1 text-[#8b949e]">{line.operation}</span>
                          )}
                          <span className="text-[#c9d1d9] truncate">{line.description}</span>
                          {isRef && lineStatus.get(line.line_no) === "resolved" && (
                            <CheckCircle className="h-3.5 w-3.5 text-green-400 shrink-0" />
                          )}
                          {isRef && lineStatus.get(line.line_no) === "needs-review" && (
                            <XIcon className="h-3.5 w-3.5 text-red-400 shrink-0" />
                          )}
                        </div>
                        <div className="mt-0.5 flex items-center gap-2 flex-wrap text-[#484f58]">
                          {line.part_type && <PartTypeBadge part_type={line.part_type} />}
                          {line.part_number && <span>PN: {line.part_number}</span>}
                          {typeof line.quantity === 'number' && line.quantity > 0 && <span>Qty: {line.quantity}</span>}
                          {typeof line.part_price === 'number' && line.part_price > 0 && <span>Part: ${line.part_price}</span>}
                          {typeof line.labor_hours === 'number' && line.labor_hours !== 0 && <span>Lab: {line.labor_hours}h</span>}
                          {typeof line.paint_hours === 'number' && line.paint_hours !== 0 && <span>Pnt: {line.paint_hours}h</span>}
                          {typeof line.total === 'number' && line.total > 0 && <span className="text-[#c9d1d9]">${line.total}</span>}
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
