"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, AlertTriangle, CheckCircle } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API_KEY="pa_dev_key"

interface ParsedLine {
  line_no: string
  is_header?: boolean
  panel_name?: string
  description?: string
  operation?: string
  part_number?: string
  quantity?: number
  part_price?: number
  labor_hours?: number
  paint_hours?: number
  total?: number
  part_type?: string
  flag?: string
}

interface Finding {
  id: string
  rule_id: string
  category: string
  severity: string
  description: string
  line_numbers: number[]
  applies: boolean
  status: string
  suggested_fix: string | null
}

interface QCPacket {
  id: string
  claim_number: string | null
  vehicle: string
  status: string
  findings_count: number
  photo_total: number
  photo_vin: number
  photo_odometer: number
  photo_damage: number
  carrier_confidence_score: number
  carrier_ready: boolean
  rejection_reasons: string[]
  auditor_note: string | null
  parsed_lines: ParsedLine[] | null
  findings: Finding[]
  parsed_metadata: Record<string, any> | null
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-500/20 text-red-400",
    high: "bg-orange-500/20 text-orange-400",
    medium: "bg-yellow-500/20 text-yellow-400",
    low: "bg-blue-500/20 text-blue-400",
  }
  return <span className={"rounded px-2 py-0.5 text-xs font-medium " + (colors[severity] || colors.low)}>{severity}</span>
}

function StatusToggle({ findingId, status, onChange }: { findingId: string; status: string; onChange: (id: string, s: string) => void }) {
  const options = ["accepted", "overridden", "rejected"]
  const labels: Record<string, string> = { accepted: "Accept", overridden: "Override", rejected: "Reject" }
  const colors: Record<string, string> = {
    accepted: "bg-green-500/20 text-green-400 border-green-500/30",
    overridden: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    rejected: "bg-red-500/20 text-red-400 border-red-500/30",
  }

  return (
    <div className="flex gap-1">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onChange(findingId, opt)}
          className={"rounded border px-2 py-0.5 text-xs font-medium transition-colors " + (status === opt ? colors[opt] : "border-[#21262d] text-[#484f58] hover:text-[#8b949e]")}
        >
          {labels[opt]}
        </button>
      ))}
    </div>
  )
}

export default function QCDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [packet, setPacket] = React.useState<QCPacket | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState("")
  const [activeTab, setActiveTab] = React.useState<"findings" | "lines">("findings")
  const [auditorNote, setAuditorNote] = React.useState("")
  const [noteSaving, setNoteSaving] = React.useState(false)
  const [noteSaved, setNoteSaved] = React.useState(false)
  const [findings, setFindings] = React.useState<Finding[]>([])

  const id = params.id

  function loadPacket() {
    fetch(API_URL + "/api/qc/" + id, { headers: { "X-API-Key": API_KEY } })
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then((data: QCPacket) => {
        setPacket(data)
        setFindings(data.findings || [])
        setAuditorNote(data.auditor_note || "")
        setLoading(false)
      })
      .catch((err) => {
        setError(typeof err === "number" ? "HTTP " + err : err.message || "Failed to load")
        setLoading(false)
      })
  }

  React.useEffect(() => { loadPacket() }, [id])

  function updateFindingStatus(findingId: string, newStatus: string) {
    setFindings((prev) => prev.map((f) => f.id === findingId ? { ...f, status: newStatus } : f))
    fetch(API_URL + "/api/qc/" + id + "/findings/" + findingId, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
      body: JSON.stringify({ status: newStatus }),
    }).catch(() => {})
  }

  async function saveNote() {
    setNoteSaving(true)
    setNoteSaved(false)
    try {
      const r = await fetch(API_URL + "/api/qc/" + id + "/note", {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
        body: JSON.stringify({ auditor_note: auditorNote }),
      })
      if (!r.ok) throw new Error("Failed")
      setNoteSaved(true)
      setTimeout(() => setNoteSaved(false), 2000)
    } catch (e) {
      setError("Failed to save note")
    } finally {
      setNoteSaving(false)
    }
  }

  if (loading) return <div className="p-6 text-sm text-[#8b949e]">Loading...</div>
  if (error) return <div className="p-6 text-sm text-red-400">Error: {error}</div>
  if (!packet) return <div className="p-6 text-sm text-[#8b949e]">Not found</div>

  const findingsByCat = findings.reduce((acc: Record<string, Finding[]>, f) => {
    const cat = f.category
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(f)
    return acc
  }, {})

  const catLabels: Record<string, string> = {
    photo_coverage: "Photo Coverage",
    completeness: "Estimate Completeness",
    state_compliance: "State Compliance",
    exception: "Exceptions & Modifications",
  }

  const lines = packet.parsed_lines || []

  return (
    <div className="p-6">
      <div className="mb-6">
        <button onClick={() => router.push("/qc")} className="mb-3 flex items-center gap-1 text-sm text-[#8b949e] hover:text-[#c9d1d9]">
          <ArrowLeft className="h-4 w-4" />
          Back to QC
        </button>
        <h1 className="text-xl font-semibold text-[#c9d1d9]">{packet.claim_number || "Untitled QC Packet"}</h1>
        <p className="text-sm text-[#8b949e]">{packet.vehicle}</p>
      </div>

      {/* Carrier Confidence Score */}
      <div className="mb-6 rounded-lg border border-[#21262d] bg-[#161b22] p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[#8b949e]">Carrier Confidence</p>
            <div className="mt-2 flex items-baseline gap-2">
              <span className={"text-4xl font-bold " + (packet.carrier_ready ? "text-green-400" : "text-red-400")}>
                {packet.carrier_confidence_score}
              </span>
              <span className="text-lg text-[#484f58]">/100</span>
            </div>
          </div>
          <div className={"rounded-full px-4 py-2 text-sm font-semibold " + (packet.carrier_ready ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400")}>
            {packet.carrier_ready ? "✓ Ready for Carrier" : "✗ Not Ready"}
          </div>
        </div>

        {packet.rejection_reasons && packet.rejection_reasons.length > 0 && (
          <div className="mt-4 border-t border-[#21262d] pt-4">
            <p className="mb-2 text-xs font-semibold text-[#8b949e] uppercase">Rejection Reasons</p>
            <ul className="space-y-1">
              {packet.rejection_reasons.map((reason, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-[#c9d1d9]">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400" />
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-1 border-b border-[#21262d]">
        {[
          { key: "findings", label: "Findings (" + packet.findings_count + ")" },
          { key: "lines", label: "Estimate Lines (" + lines.length + ")" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={"px-4 py-2 text-sm transition-colors " + (activeTab === tab.key ? "border-b-2 border-[#f0883e] text-[#f0883e]" : "text-[#8b949e] hover:text-[#c9d1d9]")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Findings Tab with toggles */}
      {activeTab === "findings" && (
        <div className="space-y-4">
          {packet.findings_count === 0 ? (
            <div className="flex items-center gap-2 text-green-400">
              <CheckCircle className="h-5 w-5" />
              <span className="text-sm font-semibold">No exceptions — packet passes QC</span>
            </div>
          ) : (
            Object.entries(findingsByCat).map(([cat, catFindings]) => (
              <div key={cat}>
                <h3 className="mb-2 text-sm font-semibold text-[#c9d1d9]">{catLabels[cat] || cat}</h3>
                <div className="space-y-2">
                  {catFindings.map((f) => (
                    <div key={f.id} className="rounded-lg border border-[#21262d] bg-[#161b22] p-3">
                      <div className="mb-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-[#484f58]">{f.rule_id}</span>
                          <SeverityBadge severity={f.severity} />
                          {f.line_numbers?.length > 0 && (
                            <span className="text-xs text-[#484f58]">L{f.line_numbers.join(", ")}</span>
                          )}
                        </div>
                        <StatusToggle findingId={f.id} status={f.status} onChange={updateFindingStatus} />
                      </div>
                      <p className="mb-1 text-sm text-[#c9d1d9]">{f.description}</p>
                      {f.suggested_fix && (
                        <p className="text-xs text-[#8b949e]">Fix: {f.suggested_fix}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}

          {/* Auditor Note + Submit */}
          <div className="mt-6 rounded-lg border border-[#21262d] bg-[#161b22] p-6">
            <h3 className="mb-3 text-sm font-semibold text-[#c9d1d9]">Submit QC Report</h3>
            <div className="mb-3">
              <label className="mb-1 block text-xs text-[#8b949e]">Rejection Note / Message to Auditor</label>
              <textarea
                value={auditorNote}
                onChange={(e) => setAuditorNote(e.target.value)}
                rows={4}
                className="w-full rounded border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#58a6ff] resize-y"
                placeholder="Enter rejection note or message for the auditor..."
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={saveNote}
                disabled={noteSaving}
                className="inline-flex items-center gap-2 rounded border border-[#30363d] bg-[#21262d] px-4 py-2 text-sm text-[#c9d1d9] hover:bg-[#30363d] disabled:opacity-50"
              >
                {noteSaving ? "Saving..." : noteSaved ? "✓ Saved" : "Submit & Generate Report"}
              </button>
              {noteSaved && <span className="text-xs text-green-400">Report generated — copy the rejection note above</span>}
            </div>
          </div>

        </div>
      )}

      {/* Lines Tab */}
      {activeTab === "lines" && (
        <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-2">
          <div className="space-y-0.5 max-h-[70vh] overflow-y-auto">
            {lines.length === 0 ? (
              <p className="px-3 py-4 text-sm text-[#8b949e]">No parsed lines.</p>
            ) : (
              lines.map((line, idx) => {
                const isHeader = line.is_header
                const bg = isHeader ? "bg-[#21262d] font-semibold" : "hover:bg-[#0d1117]"
                if (isHeader) {
                  return (
                    <div key={idx} className={"rounded px-3 py-1.5 text-sm text-[#c9d1d9] " + bg}>
                      <span className="text-[#8b949e] mr-2">{line.line_no}</span>
                      {line.panel_name || line.description || ""}
                    </div>
                  )
                }
                return (
                  <div key={idx} className={"flex items-start gap-3 rounded px-3 py-1.5 text-xs " + bg}>
                    <span className="font-mono min-w-[2ch] text-right shrink-0 text-[#484f58]">{line.line_no}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 truncate">
                        {line.flag && <span className="text-[#f0883e] font-bold">{line.flag}</span>}
                        {line.operation && <span className="rounded bg-[#21262d] px-1 text-[#8b949e]">{line.operation}</span>}
                        <span className="text-[#c9d1d9] truncate">{line.description}</span>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}

    </div>
  )
}
