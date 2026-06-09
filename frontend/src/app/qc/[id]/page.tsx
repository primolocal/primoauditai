"use client"

import React, { useState, useEffect, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, CheckCircle, Clock, AlertTriangle, ClipboardCheck, ExternalLink, ChevronDown } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://primoauditai-production.up.railway.app"
const API_KEY = (process.env.NEXT_PUBLIC_API_KEY || "pa_dev") as string

interface Line {
  line_no: number | string
  description: string
  operation?: string
  part_number?: string
  part_type?: string  // "OE", "OEM", "LKQ", "USED", "A/M", "REM", "REC", etc.
  part_price?: number
  labor_hours?: number
  paint_hours?: number
  flag?: string       // manual entry indicator
  is_header?: boolean
}

interface Finding {
  id: string
  rule_id: string
  category: string  // "completeness", "confidence", "coverage", "exception"
  severity: string  // "critical", "high", "medium", "low"
  description: string
  suggested_fix?: string
  line_numbers: (string | number)[]
  status: "pending" | "accepted" | "overridden" | "rejected"
  applies: boolean
}

interface QCPacket {
  id: string
  claim_number: string
  status: string
  created_at: string
  carrier_confidence_score: number
  carrier_ready: boolean
  photo_type: string | null
  auto_rejected: boolean
  findings_count: number
  parsed_lines: Line[] | null
  parsed_metadata: Record<string, any> | null
  findings: Finding[]
  rejection_reasons: string[]
  auditor_note: string | null
  photo_verified: {
    vin_photo_present: boolean
    odometer_photo_present: boolean
    damage_photos_present: boolean
  } | null
  photos: Photo[]
}

interface Photo {
  id: string
  filename: string
  photo_type?: string
  photo_location?: string
  confidence?: number
  width: number
  height: number
  page_num: number
  image_index?: number
  matched_lines?: number[]
  thumbnail?: string
}

/* ─────────────────────────── */

function StatusToggle({ findingId, status, onChange }: { findingId: string; status: string; onChange: (id: string, status: string) => void }) {
  const options = ["accepted", "overridden", "rejected"]
  const colors: Record<string, string> = {
    accepted: "bg-green-500/20 border-green-500/30 text-green-400",
    overridden: "bg-yellow-500/20 border-yellow-500/30 text-yellow-400",
    rejected: "bg-red-500/20 border-red-500/30 text-red-400",
  }
  const labels: Record<string, string> = {
    accepted: "Accept", overridden: "Override", rejected: "Reject",
  }
  return (
    <div className="flex gap-1">
      {options.map((opt) => (
        <button key={opt} onClick={() => onChange(findingId, opt)}
          className={"rounded border px-2 py-0.5 text-xs font-medium transition-colors " + (status === opt ? colors[opt] : "border-[#21262d] text-[#484f58] hover:text-[#8b949e]")}>
          {labels[opt]}
        </button>
      ))}
    </div>
  )
}

/* ─────────────────────────── */

export default function QCDetailPage() {
  const { id } = useParams() as { id: string }
  const router = useRouter()
  const [packet, setPacket] = React.useState<QCPacket | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState("")
  const [auditorNote, setAuditorNote] = React.useState("")
  const [noteSaving, setNoteSaving] = React.useState(false)
  const [noteSaved, setNoteSaved] = React.useState(false)
  const [copied, setCopied] = React.useState(false)
  const [activeTab, _setActiveTab] = React.useState<"review" | "photos">("review")

  // Fetch detail
  const load = async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API_URL}/api/qc/${id}`, { headers: { "X-API-Key": API_KEY } })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const d = await r.json()
      setPacket(d)
      setAuditorNote(d.auditor_note || "")
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function updateFindingStatus(fid: string, status: string) {
    try {
      await fetch(`${API_URL}/api/qc/${id}/findings/${fid}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
        body: JSON.stringify({ status }),
      })
      await load()
    } catch (e) {
      console.error(e)
    }
  }

  async function saveNote() {
    if (!packet) return
    setNoteSaving(true)
    try {
      await fetch(`${API_URL}/api/qc/${id}/note`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
        body: JSON.stringify({ auditor_note: auditorNote }),
      })
      setNoteSaved(true)
      setTimeout(() => setNoteSaved(false), 2000)
    } catch (e) {
      console.error(e)
    } finally {
      setNoteSaving(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!packet) return
    if (!window.confirm("Submit QC report? This marks the packet as reviewed.")) return
    try {
      const payload: any = { auditor_note: auditorNote || null }
      const r = await fetch(`${API_URL}/api/qc/${id}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const d = await r.json()
      alert(d.message || "Submitted")
      router.push("/qc")
    } catch (e: any) {
      alert(e.message)
    }
  }

  async function handleCopyNote() {
    const note = buildNoteText()
    await navigator.clipboard.writeText(note)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function buildNoteText(): string {
    if (!packet) return ""
    const lines = [
      `Claim: ${packet.claim_number}`,
      `Score: ${packet.carrier_confidence_score}/100 — ${packet.carrier_ready ? "✅ READY" : "❌ NOT READY"}`,
      `Findings: ${packet.findings_count}`,
    ]
    if (packet.rejection_reasons.length) {
      lines.push(`Rejection Reasons:`, ...packet.rejection_reasons.map(r => `  - ${r}`))
    }
    if (packet.auditor_note) lines.push(`Note: ${packet.auditor_note}`)
    return lines.join(" | ")
  }

  React.useEffect(() => { load() }, [id])

  if (loading) return <div className="p-8 text-[#8b949e]">Loading…</div>
  if (error) return <div className="p-8 text-red-400">Error: {error}</div>
  if (!packet) return <div className="p-8 text-[#8b949e]">Packet not found</div>

  const lines: Line[] = packet.parsed_lines || []
  const findings = packet.findings || []
  const catLabels: Record<string, string> = {
    completeness: "Estimate Completeness",
    confidence:   "Carrier Confidence",
    exception:    "Exceptions & Modifications",
    coverage:     "Photo Coverage",
  }
  const findingsByCat: Record<string, Finding[]> = {}
  for (const f of findings) {
    const c = f.category
    if (!findingsByCat[c]) findingsByCat[c] = []
    findingsByCat[c].push(f)
  }

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#c9d1d9]">
      {/* ── Header ── */}
      <div className="border-b border-[#21262d] bg-[#161b22] px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/qc")} className="text-[#8b949e] hover:text-[#c9d1d9]">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-sm font-semibold text-[#c9d1d9]">QC Review: {packet.claim_number}</h1>
            <p className="text-xs text-[#484f58]">ID: {packet.id.slice(0, 8)}… · {new Date(packet.created_at).toLocaleDateString()}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {packet.carrier_ready ? (
            <span className="flex items-center gap-1.5 rounded bg-green-500/20 px-2 py-1 text-xs font-semibold text-green-400">
              <CheckCircle className="h-3.5 w-3.5" /> Ready for Carrier
            </span>
          ) : (
            <span className="flex items-center gap-1.5 rounded bg-red-500/20 px-2 py-1 text-xs font-semibold text-red-400">
              <AlertTriangle className="h-3.5 w-3.5" /> Needs Review
            </span>
          )}
          <span className="text-xs text-[#8b949e]">Score: <span className="font-bold text-[#c9d1d9]">{packet.carrier_confidence_score}</span>/100</span>
          <span className="text-xs text-[#484f58]">· {findings.length} finding{findings.length !== 1 && "s"}</span>
        </div>
      </div>

      {/* ── Tab Bar ── */}
      <div className="border-b border-[#21262d] px-4 bg-[#161b22] flex gap-1">
        <button onClick={() => _setActiveTab("review")}
          className={"px-4 py-2 text-sm transition-colors border-b-2 " + (activeTab === "review" ? "border-[#f0883e] text-[#f0883e]" : "border-transparent text-[#8b949e] hover:text-[#c9d1d9]")}>
          Review
        </button>
        <button onClick={() => _setActiveTab("photos")}
          className={"px-4 py-2 text-sm transition-colors border-b-2 " + (activeTab === "photos" ? "border-[#f0883e] text-[#f0883e]" : "border-transparent text-[#8b949e] hover:text-[#c9d1d9]")}>
          Photos ({packet.photos?.length || 0})
        </button>
      </div>

      {/* ── Content ── */}
      <div className="mx-auto max-w-7xl p-4">

        {/* REVIEW TAB */}
        {activeTab === "review" && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 items-start">
            {/* Left column: Findings */}
            <div>
              <h2 className="mb-3 text-sm font-semibold text-[#c9d1d9]">Findings ({packet.findings_count})</h2>
              {packet.findings_count === 0 ? (
                <div className="flex items-center gap-2 text-green-400"><CheckCircle className="h-5 w-5" /><span className="text-sm font-semibold">No exceptions — packet passes QC</span></div>
              ) : (
                <div className="space-y-4">
                  {Object.entries(findingsByCat).map(([cat, catFindings]) => (
                    <div key={cat}>
                      <h3 className="mb-2 text-sm font-semibold text-[#c9d1d9]">{catLabels[cat] || cat}</h3>
                      <div className="space-y-2">
                        {catFindings.map((f) => (
                          <div key={f.id} className="rounded-lg border border-[#21262d] bg-[#161b22] p-3">
                            <div className="mb-2 flex items-start justify-between">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="rounded bg-[#30363d] px-1.5 py-0.5 text-[10px] font-mono font-bold text-[#c9d1d9]">{f.rule_id}</span>
                                  {f.line_numbers?.length > 0 && <span className="text-[10px] text-[#58a6ff]">{f.line_numbers.map(String).join(", ")}</span>}
                                  <span className={`rounded px-1.5 py-0 text-[10px] font-semibold ${
                                    f.severity === "critical" || f.severity === "high" ? "bg-red-500/20 text-red-400"
                                    : f.severity === "medium" ? "bg-yellow-500/20 text-yellow-400"
                                    : "bg-blue-500/20 text-blue-400"}`}>
                                    {f.severity}
                                  </span>
                                </div>
                                <p className="mt-1 text-sm text-[#c9d1d9]">{f.description}</p>
                                {f.suggested_fix && <p className="mt-1 text-xs text-[#58a6ff]">Fix: {f.suggested_fix}</p>}
                              </div>
                              <StatusToggle findingId={f.id} status={f.status} onChange={updateFindingStatus} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Right column */}
            <div className="space-y-4">
              {/* Metadata */}
              <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
                <h3 className="mb-2 text-xs font-semibold uppercase text-[#484f58]">Estimate Metadata</h3>
                {packet.parsed_metadata && (
                  <div className="space-y-1 text-xs text-[#8b949e]">
                    {Object.entries(packet.parsed_metadata).filter(([k]) => !["license_plate", "vin", "state"].includes(k)).map(([k, v]) => (
                      <div key={k}>{k}: <span className="text-[#c9d1d9]">{v || "N/A"}</span></div>
                    ))}
                  </div>
                )}
              </div>

              {/* Estimate Lines */}
              <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
                <h3 className="mb-2 text-xs font-semibold uppercase text-[#484f58]">Estimate Lines ({lines.length})</h3>
                <div className="max-h-96 space-y-1 overflow-y-auto">
                  {lines.map((line) => (
                    <div key={line.line_no} className="rounded bg-[#0d1117] p-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[#484f58]">{line.line_no}</span>
                        {line.operation && <span className="rounded bg-[#21262d] px-1.5 py-0.5 text-[#8b949e]">{line.operation}</span>}
                      </div>
                      <div className="mt-0.5 truncate text-[#c9d1d9]">{line.description}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Auditor Note */}
              <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
                <h3 className="mb-2 text-xs font-semibold uppercase text-[#484f58]">Rejection Note / Message to Auditor</h3>
                <textarea value={auditorNote} onChange={(e) => setAuditorNote(e.target.value)} rows={4}
                  placeholder="Add a note explaining rejections or overrides..."
                  className="w-full rounded border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#58a6ff]" />
                <div className="mt-2 flex gap-2">
                  <button onClick={saveNote} disabled={noteSaving}
                    className="rounded bg-[#1f6feb] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#388bfd] disabled:opacity-50">
                    {noteSaving ? "Saving…" : "Save Note"}
                  </button>
                  <button onClick={handleCopyNote} className="rounded border border-[#30363d] px-3 py-1.5 text-xs text-[#8b949e] hover:text-[#c9d1d9]">
                    {copied ? "Copied!" : "Copy Note"}
                  </button>
                  {noteSaved && <span className="flex items-center gap-1 text-xs text-green-400"><CheckCircle className="h-3 w-3" />Saved</span>}
                </div>
              </div>

              {/* Submit */}
              <div className="rounded-lg border border-[#21262d] bg-[#161b22] p-4">
                <div className="mb-3 text-sm font-semibold text-[#c9d1d9]">{buildNoteText()}</div>
                <form onSubmit={handleSubmit}>
                  <button type="submit" className="w-full rounded bg-[#1f6feb] px-3 py-2 text-sm font-semibold text-white hover:bg-[#388bfd]">
                    Submit & Generate Report
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* PHOTOS TAB */}
        {activeTab === "photos" && (
          <div>
            <h3 className="mb-3 text-sm font-semibold text-[#c9d1d9]">Extracted Photos ({packet.photos?.length || 0})</h3>
            {packet.photos?.length > 0 ? (
              <div className="grid grid-cols-3 gap-3">
                {packet.photos.map((p) => {
                  const typeBadge: Record<string, string> = {
                    vin: "bg-green-500/20 text-green-400 border-green-500/30",
                    odometer: "bg-blue-500/20 text-blue-400 border-blue-500/30",
                    damage: "bg-orange-500/20 text-orange-400 border-orange-500/30",
                    other: "bg-gray-500/20 text-gray-400 border-gray-500/30",
                  }
                  return (
                    <div key={p.id} className="group relative overflow-hidden rounded-xl border border-[#30363d] bg-[#161b22] shadow-lg transition-all hover:border-[#484f58] hover:shadow-xl">
                      {/* ── Thumbnail ── */}
                      <div className="relative aspect-square overflow-hidden bg-[#0d1117]">
                        {p.thumbnail ? (
                          <a href={p.thumbnail} target="_blank" rel="noopener noreferrer" className="block w-full h-full">
                            <img src={p.thumbnail} alt={p.filename} className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
                            {/* Zoom hint on hover */}
                            <div className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/30">
                              <span className="opacity-0 transition-opacity group-hover:opacity-100 text-[10px] font-medium text-white bg-black/60 px-2 py-1 rounded-full">🔍 Click to enlarge</span>
                            </div>
                          </a>
                        ) : (
                          <div className="flex h-full items-center justify-center">
                            <span className="text-xs text-[#484f58]">No preview</span>
                          </div>
                        )}
                        {/* Top-right: delete + size */}
                        <div className="absolute top-1.5 right-1.5 flex items-center gap-1">
                          <button
                            onClick={async () => {
                              if (!confirm("Remove this photo?")) return
                              await fetch(`${API_URL}/api/qc/` + id + `/photos/` + p.id, { method: "DELETE", headers: { "X-API-Key": API_KEY } })
                              await load()
                            }}
                            className="rounded bg-red-500/50 px-1.5 py-0.5 text-[9px] font-bold text-white opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-500"
                          >
                            ✕
                          </button>
                          <span className="rounded bg-black/60 px-1.5 py-0.5 text-[9px] text-[#8b949e] backdrop-blur">
                            {p.width}×{p.height}
                          </span>
                        </div>
                      </div>

                      {/* ── Body ── */}
                      <div className="p-2.5 space-y-2">
                        {/* Row 1: Badge + Confidence */}
                        <div className="flex items-center gap-2">
                          <span className={"shrink-0 truncate rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider " + (typeBadge[p.photo_type || "other"] || typeBadge.other)}>
                            {p.photo_type || "other"}
                          </span>
                          {p.confidence != null && (
                            <div className="flex flex-1 items-center gap-1.5">
                              <div className="h-2 flex-1 rounded-full bg-[#21262d] overflow-hidden">
                                <div
                                  className={"h-full rounded-full transition-all " + (p.confidence >= 0.85 ? "bg-green-500" : p.confidence >= 0.6 ? "bg-yellow-500" : "bg-red-500")}
                                  style={{ width: `${Math.round(p.confidence * 100)}%` }}
                                />
                              </div>
                              <span className="shrink-0 text-[10px] font-mono text-[#8b949e]">{Math.round(p.confidence * 100)}%</span>
                            </div>
                          )}
                        </div>

                        {/* Location */}
                        <div className="flex items-center gap-1.5">
                          <span className="shrink-0 text-[10px]">📍</span>
                          <input
                            type="text"
                            defaultValue={p.photo_location && p.photo_location !== "unknown" ? p.photo_location : ""}
                            placeholder="set location..."
                            onBlur={async (e) => {
                              const newLoc = e.target.value.trim()
                              if (!newLoc || newLoc === p.photo_location) return
                              await fetch(`${API_URL}/api/qc/` + id + `/photos/` + p.id + `/location`, {
                                method: "PATCH",
                                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                                body: JSON.stringify({ photo_location: newLoc }),
                              })
                              await load()
                            }}
                            className="w-full border-b border-dashed border-[#30363d] bg-transparent py-0.5 text-[10px] text-[#8b949e] outline-none focus:border-[#58a6ff] focus:text-[#c9d1d9]"
                          />
                        </div>

                        {/* Row 3: Matched Lines — prominent when present */}
                        {p.matched_lines && p.matched_lines.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            <span className="text-[9px] uppercase tracking-wide text-[#484f58]">Lines:</span>
                            {p.matched_lines.map((ln) => (
                              <span key={ln} className="rounded bg-[#1f6feb]/20 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-[#58a6ff]">
                                #{ln}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* ── Divider ── */}
                        <div className="border-t border-[#21262d]" />

                        {/* ── Controls ── */}
                        <div className="space-y-1.5">
                          <label className="block text-[9px] uppercase tracking-wider text-[#484f58]">Override Type</label>
                          <select
                            value={p.photo_type || "other"}
                            onChange={async (e) => {
                              const newType = e.target.value
                              await fetch(`${API_URL}/api/qc/` + id + `/photos/` + p.id + `/type`, {
                                method: "PATCH",
                                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                                body: JSON.stringify({ photo_type: newType }),
                              })
                              await load()
                            }}
                            className="w-full rounded-lg border border-[#30363d] bg-[#0d1117] px-2 py-1 text-xs text-[#c9d1d9] outline-none focus:border-[#58a6ff]"
                          >
                            {[
                              { value: "other", label: "🔄 Other / Unsure" },
                              { value: "vin", label: "🔢 VIN Plate" },
                              { value: "odometer", label: "🚘 Odometer" },
                              { value: "damage", label: "⚠️ Damage (General)" },
                              { value: "dent", label: "🔨 Dent" },
                              { value: "scratch", label: "🖊️ Scratch" },
                              { value: "crack", label: "💔 Crack / Break" },
                              { value: "rust", label: "🟤 Rust / Corrosion" },
                              { value: "glass", label: "🪟 Glass / Mirror" },
                              { value: "tire", label: "🛞 Tire / Wheel" },
                            ].map((opt) => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        </div>

                        {/* ── Footer meta ── */}
                        <div className="flex items-center justify-between pt-0.5">
                          <span className="text-[9px] text-[#484f58]">Page {p.page_num}</span>
                          {p.image_index && (
                            <span className="text-[9px] text-[#484f58]">#{p.image_index}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
              </div>
            ) : (
              <p className="text-sm text-[#8b949e]">No photos extracted. Upload an image PDF with the estimate on the QC upload page.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
