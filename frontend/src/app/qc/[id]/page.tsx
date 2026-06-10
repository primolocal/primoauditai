"use client"

import React, { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://primoauditai-production.up.railway.app"
const API_KEY = (process.env.NEXT_PUBLIC_API_KEY || "pa_dev") as string

// ── Types ──
interface Line {
  line_no: number | string
  description: string
  operation?: string
  panel_name?: string
  part_type?: string
  is_header?: boolean
}
interface Finding {
  id: string; rule_id: string; category: string; severity: string
  description: string; suggested_fix?: string; line_numbers: (string|number)[]
  status: string; applies: boolean
}
interface Photo {
  id: string; filename: string; photo_type?: string; photo_location?: string
  confidence?: number; width: number; height: number; page_num: number
  image_index?: number; matched_lines?: number[]; thumbnail?: string
}
interface QCPacket {
  id: string; claim_number: string; carrier_confidence_score: number
  carrier_ready: boolean; findings_count: number; photo_total: number
  findings: Finding[]; photos: Photo[]; parsed_lines?: Line[]
  auditor_note?: string; created_at: string
}

const typeColors: Record<string, string> = {
  vin: "bg-green-500/20 text-green-400 border-green-500/30",
  odometer: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  damage: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  needs_review: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  dent: "bg-red-500/20 text-red-400 border-red-500/30",
  scratch: "bg-red-500/20 text-red-400 border-red-500/30",
  crack: "bg-red-500/20 text-red-400 border-red-500/30",
  rust: "bg-red-500/20 text-red-400 border-red-500/30",
  corrosion: "bg-red-500/20 text-red-400 border-red-500/30",
  other: "bg-gray-500/20 text-gray-400 border-gray-500/30",
}

export default function QCDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [packet, setPacket] = useState<QCPacket | null>(null)
  const [selected, setSelected] = useState<Photo | null>(null)
  const [selLines, setSelLines] = useState<number[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    const r = await fetch(`${API_URL}/api/qc/${id}`, { headers: { "X-API-Key": API_KEY } })
    const d = await r.json()
    setPacket(d)
    if (!selected && d.photos?.length > 0) {
      setSelected(d.photos[0])
      setSelLines(d.photos[0].matched_lines || [])
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [id])

  if (loading || !packet) {
    return <div className="flex h-screen items-center justify-center bg-[#0d1117] text-[#8b949e]">Loading...</div>
  }

  const photos: Photo[] = packet.photos || []
  const lines: Line[] = (packet.parsed_lines || []).filter((l: Line) => !l.is_header)
  const findings = packet.findings || []

  const selectPhoto = (p: Photo) => { setSelected(p); setSelLines(p.matched_lines || []) }

  const updateType = async (pid: string, t: string) => {
    await fetch(`${API_URL}/api/qc/${id}/photos/${pid}/type`, {
      method: "PATCH", headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
      body: JSON.stringify({ photo_type: t }),
    })
    await load()
  }

  const updateLoc = async (pid: string, loc: string) => {
    await fetch(`${API_URL}/api/qc/${id}/photos/${pid}/location`, {
      method: "PATCH", headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
      body: JSON.stringify({ photo_location: loc }),
    })
    await load()
  }

  const toggleLine = (ln: number) => {
    setSelLines(prev => prev.includes(ln) ? prev.filter(l => l !== ln) : [...prev, ln])
  }

  const TypeBadge = ({ t }: { t?: string }) => (
    <span className={"inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase " + (typeColors[t || "other"] || typeColors.other)}>
      {t || "review"}
    </span>
  )

  return (
    <div className="flex h-screen flex-col bg-[#0d1117] text-[#c9d1d9]">
      {/* ── TOP BAR ── */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-[#21262d] bg-[#161b22] px-4">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/qc")} className="text-[#8b949e] hover:text-[#c9d1d9]"><ArrowLeft className="h-5 w-5" /></button>
          <span className="text-sm font-semibold">{packet.claim_number}</span>
          <span className="text-xs text-[#8b949e]">
            Score: <span className={packet.carrier_confidence_score >= 158 ? "text-green-400" : "text-red-400"}>
              {packet.carrier_confidence_score}/225
            </span>
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-[#8b949e]">
          <span>{findings.length} findings</span>
          <span>{photos.length} photos</span>
        </div>
      </div>

      {/* ── THREE-PANEL BODY ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* LEFT: Photo thumbnails */}
        <div className="w-[220px] shrink-0 overflow-y-auto border-r border-[#21262d] p-2">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[#484f58]">Photos</div>
          <div className="grid grid-cols-2 gap-1.5">
            {photos.map((p) => (
              <div key={p.id} onClick={() => selectPhoto(p)}
                className={"cursor-pointer overflow-hidden rounded border-2 transition-all " +
                  (selected?.id === p.id ? "border-[#58a6ff] shadow-lg shadow-[#58a6ff]/20" : "border-[#21262d] hover:border-[#484f58]")}>
                {p.thumbnail ? <img src={p.thumbnail} className="aspect-square w-full object-cover" /> :
                  <div className="flex aspect-square items-center justify-center bg-[#161b22] text-[9px] text-[#484f58]">No img</div>}
                <div className="bg-[#161b22] px-1 py-0.5">
                  <TypeBadge t={p.photo_type} />
                  {p.matched_lines && p.matched_lines.length > 0 && (
                    <span className="ml-1 text-[8px] text-[#58a6ff]">L{p.matched_lines.join(",")}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CENTER: Selected photo detail */}
        <div className="flex flex-1 flex-col overflow-y-auto bg-[#161b22]">
          {selected ? (
            <div className="flex flex-1 flex-col p-4">
              <div className="mb-4 overflow-hidden rounded-lg border border-[#21262d] bg-[#0d1117]">
                {selected.thumbnail ? (
                  <a href={selected.thumbnail} target="_blank" rel="noopener noreferrer">
                    <img src={selected.thumbnail} className="max-h-[420px] w-full object-contain" />
                  </a>
                ) : <div className="flex h-[420px] items-center justify-center text-sm text-[#484f58]">No preview</div>}
              </div>

              <div className="mb-4 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="mb-1 block text-[10px] uppercase tracking-wide text-[#484f58]">Damage Type</label>
                  <select value={selected.photo_type || "needs_review"} onChange={(e) => updateType(selected.id, e.target.value)}
                    className="w-full rounded border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-sm text-[#c9d1d9]">
                    <option value="needs_review">🔍 Needs Review</option>
                    <option value="dent">🔨 Dent</option>
                    <option value="scratch">🖊️ Scratch</option>
                    <option value="crack">💔 Crack</option>
                    <option value="rust">🟤 Rust</option>
                    <option value="corrosion">🟤 Corrosion</option>
                    <option value="damage">⚠️ Damage (General)</option>
                    <option value="vin">🔢 VIN Plate</option>
                    <option value="odometer">🚘 Odometer</option>
                    <option value="other">🔄 Other</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-[10px] uppercase tracking-wide text-[#484f58]">Location</label>
                  <input type="text" defaultValue={selected.photo_location && selected.photo_location !== "needs_review" ? selected.photo_location : ""}
                    placeholder="click to set..."
                    onBlur={(e) => { if (e.target.value.trim()) updateLoc(selected.id, e.target.value.trim()) }}
                    className="w-full rounded border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-sm text-[#c9d1d9]" />
                </div>
                <div>
                  <label className="mb-1 block text-[10px] uppercase tracking-wide text-[#484f58]">AI Confidence</label>
                  <div className="flex items-center gap-2 pt-1">
                    <div className="h-2 flex-1 rounded-full bg-[#21262d]"><div className={"h-full rounded-full " + ((selected.confidence||0)>=0.85?"bg-green-500":(selected.confidence||0)>=0.6?"bg-yellow-500":"bg-red-500")}
                      style={{width:`${Math.round((selected.confidence||0)*100)}%`}} /></div>
                    <span className="text-xs font-mono">{Math.round((selected.confidence||0)*100)}%</span>
                  </div>
                </div>
                <div>
                  <label className="mb-1 block text-[10px] uppercase tracking-wide text-[#484f58]">Page</label>
                  <span className="text-sm text-[#8b949e]">Page {selected.page_num} · {selected.width}×{selected.height}</span>
                </div>
              </div>

              <div>
                <label className="mb-2 block text-[10px] uppercase tracking-wide text-[#484f58]">Matched Lines ({selLines.length})</label>
                {selLines.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {selLines.map(ln => {
                      const line = lines.find(l => Number(l.line_no) === ln)
                      return line ? (
                        <span key={ln} className="rounded bg-[#1f6feb]/20 px-2 py-1 text-xs font-mono text-[#58a6ff]">
                          #{ln} {line.operation} {line.description?.slice(0,30)}
                        </span>
                      ) : null
                    })}
                  </div>
                ) : <p className="text-xs text-[#484f58]">Click estimate lines on the right to match to this photo.</p>}
              </div>

              {selLines.length > 0 && (
                <div className="mt-4 border-t border-[#21262d] pt-4">
                  <label className="mb-2 block text-[10px] uppercase tracking-wide text-[#484f58]">Findings for Matched Lines</label>
                  {findings.filter(f => f.line_numbers.some(ln => selLines.includes(Number(ln)))).length > 0 ? (
                    findings.filter(f => f.line_numbers.some(ln => selLines.includes(Number(ln)))).map(f => (
                      <div key={f.id} className="mb-2 rounded border border-[#21262d] bg-[#0d1117] p-2 text-xs">
                        <span className="font-semibold">{f.rule_id}</span>
                        <span className={"ml-2 rounded px-1 py-0.5 text-[10px] "+(f.severity==="high"||f.severity==="critical"?"bg-red-500/20 text-red-400":"bg-yellow-500/20 text-yellow-400")}>{f.severity}</span>
                        <p className="mt-1 text-[#8b949e]">{f.description}</p>
                        {f.suggested_fix && <p className="mt-1 text-green-400">{f.suggested_fix}</p>}
                      </div>
                    ))
                  ) : <p className="text-xs text-[#484f58]">No findings for these lines.</p>}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-1 items-center justify-center text-sm text-[#484f58]">← Select a photo</div>
          )}
        </div>

        {/* RIGHT: Estimate lines */}
        <div className="w-[280px] shrink-0 overflow-y-auto border-l border-[#21262d] p-2">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[#484f58]">Estimate ({lines.length} lines)</div>
          <div className="space-y-1">
            {lines.map(line => {
              const ln = Number(line.line_no)
              const isActive = selLines.includes(ln)
              return (
                <div key={String(line.line_no)} onClick={() => toggleLine(ln)}
                  className={"cursor-pointer rounded p-2 text-xs transition-all " +
                    (isActive ? "border border-[#58a6ff] bg-[#1f6feb]/10" : "border border-transparent hover:bg-[#161b22]")}>
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-semibold text-[#58a6ff]">#{line.line_no}</span>
                    <span className="rounded bg-[#21262d] px-1.5 py-0.5 text-[10px] text-[#8b949e]">{line.operation}</span>
                  </div>
                  <div className="mt-0.5 text-[#c9d1d9]">{line.description}</div>
                  {line.panel_name && <div className="mt-0.5 text-[10px] text-[#484f58]">{line.panel_name}</div>}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
