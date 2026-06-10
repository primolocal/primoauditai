"use client"

import React, { useState, useEffect, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Search } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://primoauditai-production.up.railway.app"
const API_KEY = (process.env.NEXT_PUBLIC_API_KEY || "pa_dev") as string

// ── Types ──
interface Line { line_no: number|string; description: string; operation?: string; panel_name?: string; part_type?: string; is_header?: boolean }
interface Finding { id: string; rule_id: string; category: string; severity: string; description: string; suggested_fix?: string; line_numbers: (string|number)[]; status: string; applies: boolean }
interface Photo { id: string; filename: string; photo_type?: string; photo_location?: string; confidence?: number; width: number; height: number; page_num: number; image_index?: number; matched_lines?: number[]; thumbnail?: string }
interface QCPacket { id: string; claim_number: string; carrier_confidence_score: number; carrier_ready: boolean; findings_count: number; photo_total: number; findings: Finding[]; photos: Photo[]; parsed_lines?: Line[]; created_at: string }

const typeColors: Record<string, string> = {
  vin: "bg-green-500/20 text-green-400 border-green-500/30", odometer: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  damage: "bg-orange-500/20 text-orange-400 border-orange-500/30", needs_review: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  dent: "bg-red-500/20 text-red-400 border-red-500/30", scratch: "bg-red-500/20 text-red-400 border-red-500/30",
  crack: "bg-red-500/20 text-red-400 border-red-500/30", rust: "bg-red-500/20 text-red-400 border-red-500/30", corrosion: "bg-red-500/20 text-red-400 border-red-500/30",
  other: "bg-gray-500/20 text-gray-400 border-gray-500/30",
}

export default function QCDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [packet, setPacket] = useState<QCPacket|null>(null)
  const [selected, setSelected] = useState<Photo|null>(null)
  const [selLines, setSelLines] = useState<number[]>([])
  const [lineFilter, setLineFilter] = useState("")
  const [loading, setLoading] = useState(true)

  const a = async (url: string, opts?: RequestInit) => {
    const r = await fetch(url, { ...opts, headers: { ...(opts?.headers||{}), "X-API-Key": API_KEY } })
    return r
  }

  const load = useCallback(async () => {
    const r = await a(`${API_URL}/api/qc/${id}`)
    const d = await r.json()
    setPacket(d)
    if (!selected && d.photos?.length > 0) { setSelected(d.photos[0]); setSelLines(d.photos[0].matched_lines || []) }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  // ── Keyboard nav ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!packet) return
      const photos = packet.photos || []
      const idx = selected ? photos.findIndex(p => p.id === selected.id) : -1
      if (e.key === "ArrowRight" && idx < photos.length - 1) { setSelected(photos[idx+1]); setSelLines(photos[idx+1].matched_lines||[]) }
      if (e.key === "ArrowLeft" && idx > 0) { setSelected(photos[idx-1]); setSelLines(photos[idx-1].matched_lines||[]) }
      if (e.key === " " || e.key === "Spacebar") { e.preventDefault(); if (selected) saveLines(selected.id, selLines) }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [selected, selLines, packet])

  const selectPhoto = (p: Photo) => { 
    if (selected) saveLines(selected.id, selLines)  // save previous before switching
    setSelected(p); setSelLines(p.matched_lines || [])
  }

  const updateType = async (pid: string, t: string) => {
    await a(`${API_URL}/api/qc/${id}/photos/${pid}/type`, { method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify({photo_type:t}) })
    await load()
  }

  const updateLoc = async (pid: string, loc: string) => {
    await a(`${API_URL}/api/qc/${id}/photos/${pid}/location`, { method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify({photo_location:loc}) })
    await load()
  }

  const saveLines = async (pid: string, lines: number[]) => {
    await a(`${API_URL}/api/qc/${id}/photos/${pid}/lines`, { method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify({matched_lines:lines}) })
  }

  const toggleLine = (ln: number) => {
    setSelLines(prev => { const n = prev.includes(ln) ? prev.filter(l=>l!==ln) : [...prev, ln]; return n })
  }

  const deletePhoto = async (pid: string) => {
    if (!confirm("Remove this photo?")) return
    await a(`${API_URL}/api/qc/${id}/photos/${pid}`, { method:"DELETE" })
    await load()
  }

  const decide = async (findingId: string, state: string, reason?: string) => {
    await a(`${API_URL}/api/qc/${id}/findings/${findingId}/decide`, { method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify({state, reason:reason||""}) })
    await load()
  }

  if (loading || !packet) return <div className="flex h-screen items-center justify-center bg-[#0d1117] text-[#8b949e]">Loading...</div>

  const photos = packet.photos || []
  const lines: Line[] = (packet.parsed_lines || []).filter((l:Line) => !l.is_header)
  const filteredLines = lineFilter ? lines.filter(l => (l.description||"").toLowerCase().includes(lineFilter.toLowerCase()) || (l.panel_name||"").toLowerCase().includes(lineFilter.toLowerCase())) : lines
  const findings = packet.findings || []

  // Health scorecard
  const confirmed = findings.filter(f => f.status === "confirmed").length
  const questioned = findings.filter(f => f.status === "questionable").length
  const overridden = findings.filter(f => f.status === "override").length
  const undecided = findings.filter(f => !f.status || f.status === "pending").length

  // Auto-generated note templates
  const getNote = (f: Finding) => {
    const lines = f.line_numbers?.join(", ") || "N/A"
    if (f.rule_id === "NATGEN_004") return `Replace OEM part on line${f.line_numbers?.length>1?"s":""} ${lines} with LKQ recycled per NatGen parts hierarchy. Vehicle does not qualify for OEM (current MY + <15K mi required).`
    if (f.rule_id === "NATGEN_001") return `Scan labor exceeds 0.5h allowance (${lines}). Reduce to 0.5h max per carrier guidelines.`
    if (f.category === "photo_coverage") return f.description
    return f.suggested_fix || f.description
  }

  const TypeBadge = ({t}:{t?:string}) => (
    <span className={"inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase "+(typeColors[t||"other"]||typeColors.other)}>{t||"review"}</span>
  )

  // Count photos per line
  const linePhotoCount: Record<number, number> = {}
  for (const p of photos) { for (const ln of (p.matched_lines||[])) { linePhotoCount[ln] = (linePhotoCount[ln]||0) + 1 } }

  return (
    <div className="flex h-screen flex-col bg-[#0d1117] text-[#c9d1d9]">
      {/* ── TOP BAR ── */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-[#21262d] bg-[#161b22] px-4">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/qc")} className="text-[#8b949e] hover:text-[#c9d1d9]"><ArrowLeft className="h-5 w-5"/></button>
          <span className="text-sm font-semibold">{packet.claim_number}</span>
          <span className="text-xs text-[#8b949e]">
            Score: <span className={packet.carrier_confidence_score>=158?"text-green-400":"text-red-400"}>{packet.carrier_confidence_score}/225</span>
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-[#8b949e]">
          <span>{findings.length} findings</span>
          <span>{photos.length} photos</span>
          <span className="text-[#484f58]">← → navigate photos</span>
        </div>
      </div>

      {/* ── THREE-PANEL BODY ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* LEFT: Photos */}
        <div className="w-[220px] shrink-0 overflow-y-auto border-r border-[#21262d] p-2">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[#484f58]">Photos ({photos.length})</div>
          <div className="grid grid-cols-2 gap-1.5">
            {photos.map((p,i) => (
              <div key={p.id} onClick={()=>selectPhoto(p)}
                className={"relative cursor-pointer overflow-hidden rounded border-2 transition-all "+(selected?.id===p.id?"border-[#58a6ff] shadow-lg shadow-[#58a6ff]/20":"border-[#21262d] hover:border-[#484f58]")}>
                <button onClick={(e)=>{e.stopPropagation();deletePhoto(p.id)}} className="absolute right-0.5 top-0.5 z-10 rounded bg-red-500/70 px-1 text-[8px] font-bold text-white opacity-0 hover:opacity-100 group-hover:opacity-100">✕</button>
                {p.thumbnail?<img src={p.thumbnail} className="aspect-square w-full object-cover"/>:<div className="flex aspect-square items-center justify-center bg-[#161b22] text-[9px] text-[#484f58]">No img</div>}
                <div className="bg-[#161b22] px-1 py-0.5"><TypeBadge t={p.photo_type}/>{p.matched_lines&&p.matched_lines.length>0&&<span className="ml-1 text-[8px] text-[#58a6ff]">L{p.matched_lines.join(",")}</span>}</div>
              </div>
            ))}
          </div>
        </div>

        {/* CENTER: Detail + Findings */}
        <div className="flex flex-1 flex-col overflow-y-auto bg-[#161b22]">
          {selected ? (
            <div className="flex flex-1 flex-col p-4">
              {/* Photo viewer */}
              <div className="mb-4 overflow-hidden rounded-lg border border-[#21262d] bg-[#0d1117] relative">
                {selected.thumbnail ? <a href={selected.thumbnail} target="_blank"><img src={selected.thumbnail} className="max-h-[350px] w-full object-contain"/></a>
                : <div className="flex h-[350px] items-center justify-center text-sm text-[#484f58]">No preview</div>}
                <div className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-1 text-[10px] text-[#8b949e]">{selected.width}×{selected.height}</div>
              </div>

              {/* Photo controls */}
              <div className="mb-4 grid grid-cols-3 gap-3 text-xs">
                <div><label className="mb-1 block text-[10px] uppercase tracking-wide text-[#484f58]">Type</label>
                  <select value={selected.photo_type||"needs_review"} onChange={e=>updateType(selected.id, e.target.value)}
                    className="w-full rounded border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-sm text-[#c9d1d9]">
                    <option value="needs_review">🔍 Needs Review</option>
                    <option value="dent">🔨 Dent</option><option value="scratch">🖊️ Scratch</option><option value="crack">💔 Crack</option>
                    <option value="rust">🟤 Rust</option><option value="corrosion">🟤 Corrosion</option><option value="damage">⚠️ Damage</option>
                    <option value="vin">🔢 VIN</option><option value="odometer">🚘 Odometer</option><option value="other">🔄 Other</option>
                  </select></div>
                <div><label className="mb-1 block text-[10px] uppercase tracking-wide text-[#484f58]">Location</label>
                  <input type="text" defaultValue={selected.photo_location&&selected.photo_location!=="needs_review"?selected.photo_location:""}
                    placeholder="set location..." onBlur={e=>{if(e.target.value.trim())updateLoc(selected.id, e.target.value.trim())}}
                    className="w-full rounded border border-[#30363d] bg-[#0d1117] px-2 py-1.5 text-sm text-[#c9d1d9]"/></div>
                <div><label className="mb-1 block text-[10px] uppercase tracking-wide text-[#484f58]">AI</label>
                  <div className="flex items-center gap-2 pt-1"><div className="h-2 flex-1 rounded-full bg-[#21262d]"><div className={"h-full rounded-full "+((selected.confidence||0)>=0.85?"bg-green-500":(selected.confidence||0)>=0.6?"bg-yellow-500":"bg-red-500")} style={{width:`${Math.round((selected.confidence||0)*100)}%`}}/></div>
                  <span className="text-xs font-mono">{Math.round((selected.confidence||0)*100)}%</span></div></div>
              </div>

              {/* Matched lines */}
              <div className="mb-4"><label className="mb-2 block text-[10px] uppercase tracking-wide text-[#484f58]">Matched Lines ({selLines.length})</label>
                {selLines.length>0?<div className="flex flex-wrap gap-1.5">{selLines.map(ln=>{const line=lines.find(l=>Number(l.line_no)===ln);return line?<span key={ln} className="rounded bg-[#1f6feb]/20 px-2 py-1 text-xs font-mono text-[#58a6ff]">#{ln} {line.operation} {line.description?.slice(0,25)}</span>:null})}</div>
                :<p className="text-xs text-[#484f58]">Click lines on the right, or press Space to save matches.</p>}</div>

              {/* Findings with decision buttons */}
              {selLines.length>0&&(
                <div className="border-t border-[#21262d] pt-4">
                  <label className="mb-2 block text-[10px] uppercase tracking-wide text-[#484f58]">Findings ({findings.filter(f=>f.line_numbers.some(ln=>selLines.includes(Number(ln)))).length})</label>
                  {findings.filter(f=>f.line_numbers.some(ln=>selLines.includes(Number(ln)))).map(f=>{
                    const statusColors: Record<string,string> = {confirmed:"border-green-500/30 bg-green-500/5",questionable:"border-yellow-500/30 bg-yellow-500/5",override:"border-purple-500/30 bg-purple-500/5"}
                    return (
                      <div key={f.id} className={"mb-2 rounded border p-3 text-xs "+(statusColors[f.status]||"border-[#21262d] bg-[#0d1117]")}>
                        <div className="flex items-center justify-between">
                          <span><span className="font-semibold">{f.rule_id}</span>
                            <span className={"ml-2 rounded px-1 py-0.5 text-[10px] "+(f.severity==="high"||f.severity==="critical"?"bg-red-500/20 text-red-400":"bg-yellow-500/20 text-yellow-400")}>{f.severity}</span>
                          </span>
                          {f.status&&f.status!=="pending"&&<span className="rounded bg-[#21262d] px-2 py-0.5 text-[10px] text-[#8b949e]">{f.status.toUpperCase()}</span>}
                        </div>
                        <p className="mt-1 text-[#8b949e]">{f.description}</p>
                        <div className="mt-2 rounded bg-[#0d1117] px-2 py-1.5 text-[10px] text-[#c9d1d9] border border-[#21262d]">📝 {getNote(f)}</div>
                        <div className="mt-2 flex gap-2">
                          <button onClick={()=>decide(f.id,"confirmed")} className="flex-1 rounded bg-green-600/20 px-2 py-1.5 text-[11px] font-semibold text-green-400 hover:bg-green-600/30">C: CONFIRM</button>
                          <button onClick={()=>decide(f.id,"questionable")} className="flex-1 rounded bg-yellow-600/20 px-2 py-1.5 text-[11px] font-semibold text-yellow-400 hover:bg-yellow-600/30">Q: QUESTION?</button>
                          <button onClick={()=>{const r=prompt("Override reason:");if(r)decide(f.id,"override",r)}} className="flex-1 rounded bg-purple-600/20 px-2 py-1.5 text-[11px] font-semibold text-purple-400 hover:bg-purple-600/30">O: OVERRIDE</button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ) : <div className="flex flex-1 items-center justify-center text-sm text-[#484f58]">← Select a photo</div>}
        </div>

        {/* RIGHT: Estimate lines + Health */}
        <div className="w-[300px] shrink-0 overflow-y-auto border-l border-[#21262d] p-2 flex flex-col">
          {/* Health scorecard */}
          <div className="mb-2 rounded border border-[#21262d] bg-[#161b22] p-2">
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[#484f58]">Health</div>
            <div className="grid grid-cols-2 gap-1 text-[10px]">
              <span className="text-green-400">✓ {confirmed} confirmed</span>
              <span className="text-yellow-400">? {questioned} questioned</span>
              <span className="text-purple-400">⊘ {overridden} overridden</span>
              <span className="text-[#8b949e]">☐ {undecided} remaining</span>
            </div>
            <div className="mt-1 h-1 rounded-full bg-[#21262d]"><div className="h-full rounded-full bg-green-500" style={{width:`${findings.length?Math.round((confirmed/ Math.max(findings.length,1))*100):0}%`}}/></div>
          </div>

          {/* Line filter */}
          <div className="relative mb-2">
            <Search className="absolute left-2 top-1.5 h-3 w-3 text-[#484f58]"/>
            <input type="text" placeholder="Filter lines..." value={lineFilter} onChange={e=>setLineFilter(e.target.value)}
              className="w-full rounded border border-[#30363d] bg-[#0d1117] py-1 pl-6 pr-2 text-xs text-[#c9d1d9] outline-none focus:border-[#58a6ff]"/>
          </div>

          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[#484f58]">Estimate ({filteredLines.length})</div>
          <div className="space-y-1 overflow-y-auto flex-1">
            {filteredLines.map(line=>{
              const ln=Number(line.line_no); const isActive=selLines.includes(ln); const pc=linePhotoCount[ln]||0
              return (
                <div key={String(line.line_no)} onClick={()=>toggleLine(ln)}
                  className={"cursor-pointer rounded p-2 text-xs transition-all "+(isActive?"border border-[#58a6ff] bg-[#1f6feb]/10":"border border-transparent hover:bg-[#161b22]")}>
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-semibold text-[#58a6ff]">#{line.line_no}</span>
                    <div className="flex items-center gap-1.5">
                      {pc>0&&<span className="rounded bg-[#21262d] px-1 text-[9px] text-[#8b949e]">{pc}📸</span>}
                      <span className="rounded bg-[#21262d] px-1.5 py-0.5 text-[10px] text-[#8b949e]">{line.operation}</span>
                    </div>
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
