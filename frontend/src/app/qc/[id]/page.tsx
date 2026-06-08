"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, AlertTriangle, CheckCircle, ClipboardCheck } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API_KEY = "pa_dev_key"

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

interface QCFindingData {
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

interface QCPhotoData {
  id: string
  filename: string
  photo_type: string | null
  width: number
  height: number
  page_num: number | null
  thumbnail: string | null
}

interface QCPacketData {
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
  findings: QCFindingData[]
  photos: QCPhotoData[]
  parsed_metadata: Record<string, any> | null
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-500/20 text-red-400",
    high: "bg-orange-500/20 text-orange-400",
    medium: "bg-yellow-500/20 text-yellow-400",
    low: "bg-blue-500/20 text-blue-400",
  }
  return <span className={`rounded px-2 py-0.5 text-xs font-medium ${colors[severity] || colors.low}`}>{severity}</span>
}

function PhotoBadge({ count, label, icon: Icon }: { count: number; label: string; icon: any }) {
  return (
    <div className="flex items-center gap-2 rounded border border-[#21262d] bg-[#161b22] px-3 py-2">
      <Icon className={count > 0 ? "h-4 w-4 text-green-400" : "h-4 w-4 text-red-400"} />
      <div>
        <p className="text-xs text-[#8b949e]">{label}</p>
        <p className={`text-sm font-semibold ${count > 0 ? "text-green-400" : "text-red-400"}`}>
          {count > 0 ? "Present" : "Missing"}
        </p>
      </div>
    </div>
  )
}

export default function QCDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [packet, setPacket] = React.useState<QCPacketData | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState("")
  const [activeTab, setActiveTab] = React.useState<"findings" | "lines" | "photos">("findings")

  const id = params.id

  React.useEffect(() => {
    fetch(`${API_URL}/api/qc/${id}`, { headers: { "X-API-Key": API_KEY } })
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then((data) => {
        setPacket(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(typeof err === "number" ? `HTTP ${err}` : err.message || "Failed to load")
        setLoading(false)
      })
  }, [id])

  if (loading) return <div className="p-6 text-sm text-[#8b949e]">Loading...</div>
  if (error) return <div className="p-6 text-sm text-red-400">Error: {error}</div>
  if (!packet) return <div className="p-6 text-sm text-[#8b949e]">Not found</div>

  const findingsByCat = packet.findings.reduce(
    (acc, f) => {
      const cat = f.category
      if (!acc[cat]) acc[cat] = []
      acc[cat].push(f)
      return acc
    },
    {} as Record<string, QCFindingData[]>
  )

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
        <button
          onClick={() => router.push("/qc")}
          className="mb-3 flex items-center gap-1 text-sm text-[#8b949e] hover:text-[#c9d1d9]"
        >
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
              <span className={`text-4xl font-bold ${packet.carrier_ready ? 'text-green-400' : 'text-red-400'}`}>
                {packet.carrier_confidence_score}
              </span>
              <span className="text-lg text-[#484f58]">/100</span>
            </div>
          </div>
          <div className={`rounded-full px-4 py-2 text-sm font-semibold ${packet.carrier_ready ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {packet.carrier_ready ? '✓ Ready for Carrier' : '✗ Not Ready'}
          </div>
        </div>

        {/* Rejection Reasons */}
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

        {/* Auditor Note */}
        <div className="mt-4 border-t border-[#21262d] pt-4">
          <p className="mb-2 text-xs font-semibold text-[#8b949e] uppercase">Auditor Note</p>
          <p className="text-sm text-[#c9d1d9]">{packet.auditor_note || 'No note provided.'}</p>
        </div>
      </div>

      {/* Photo Coverage Summary */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        <PhotoBadge count={packet.photo_vin} label="VIN Photo" icon={ClipboardCheck} />
        <PhotoBadge count={packet.photo_odometer} label="Odometer Photo" icon={ClipboardCheck} />
        <PhotoBadge count={packet.photo_damage} label="Damage Photos" icon={ClipboardCheck} />
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-1 border-b border-[#21262d]">
        {[
          { key: "findings", label: `Findings (${packet.findings_count})` },
          { key: "lines", label: `Estimate Lines (${lines.length})` },
          { key: "photos", label: `Photos (${packet.photo_total})` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2 text-sm transition-colors ${
              activeTab === tab.key
                ? "border-b-2 border-[#f0883e] text-[#f0883e]"
                : "text-[#8b949e] hover:text-[#c9d1d9]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Findings Tab */}
      {activeTab === "findings" && (
        <div className="space-y-4">
          {packet.findings_count === 0 ? (
            <div className="flex items-center gap-2 text-green-400">
              <CheckCircle className="h-5 w-5" />
              <span className="text-sm font-semibold">No exceptions — packet passes QC</span>
            </div>
          ) : (
            Object.entries(findingsByCat).map(([cat, findings]) => (
              <div key={cat}>
                <h3 className="mb-2 text-sm font-semibold text-[#c9d1d9]">{catLabels[cat] || cat}</h3>
                <div className="space-y-2">
                  {findings.map((f) => (
                    <div key={f.id} className="rounded-lg border border-[#21262d] bg-[#161b22] p-3">
                      <div className="mb-1 flex items-center gap-2">
                        <span className="text-xs font-mono text-[#484f58]">{f.rule_id}</span>
                        <SeverityBadge severity={f.severity} />
                        {f.line_numbers?.length > 0 && (
                          <span className="text-xs text-[#484f58]">L{f.line_numbers.join(", ")}</span>
                        )}
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
        </div>
      )}

      {/* Estimate Lines Tab */}
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
                    <div key={idx} className={`rounded px-3 py-1.5 text-sm text-[#c9d1d9] ${bg}`}>
                      <span className="text-[#8b949e] mr-2">{line.line_no}</span>
                      {line.panel_name || line.description || ""}
                    </div>
                  )
                }
                return (
                  <div key={idx} className="flex items-start gap-3 rounded px-3 py-1.5 text-xs hover:bg-[#0d1117]">
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

      {/* Photos Tab */}
      {activeTab === "photos" && (
        <div className="grid grid-cols-3 gap-3">
          {packet.photos.map((p) => {
            const typeColors: Record<string, string> = {
              vin: "border-green-500/30 bg-green-500/10",
              odometer: "border-green-500/30 bg-green-500/10",
              damage: "border-orange-500/30 bg-orange-500/10",
              other: "border-[#21262d] bg-[#161b22]",
            }
            return (
              <div key={p.id} className={`rounded-lg border p-3 ${typeColors[p.photo_type || "other"] || typeColors.other}`}>
                {p.thumbnail ? (
                  <img src={p.thumbnail} alt={p.filename} className="mb-2 w-full rounded object-cover" style={{ maxHeight: 200 }} />
                ) : (
                  <div className="mb-2 flex h-32 items-center justify-center rounded bg-[#21262d] text-xs text-[#484f58]">
                    No preview
                  </div>
                )}
                <p className="text-sm font-medium text-[#c9d1d9]">{p.filename}</p>
                <p className="text-xs text-[#8b949e]">Type: {p.photo_type || "unknown"}</p>
                <p className="text-xs text-[#484f58]">{p.width} x {p.height}</p>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
