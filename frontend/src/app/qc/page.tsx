"use client"

import * as React from "react"
import Link from "next/link"
import { ClipboardCheck, Clock, Upload } from "lucide-react"

function api(path: string): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL + path
  return path
}
const API_KEY="pa_dev_key";

interface QCPacket {
  id: string
  claim_number: string | null
  vehicle: string | null
  status: string
  findings_count: number
  photo_total: number
  carrier_confidence_score: number
  carrier_ready: boolean
  created_at: string
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
}

export default function QCPage() {
  const [packets, setPackets] = React.useState<QCPacket[]>([])
  const [loading, setLoading] = React.useState(false)
  const [listLoading, setListLoading] = React.useState(true)
  const [error, setError] = React.useState("")
  const [success, setSuccess] = React.useState("")

  const [estimatePdf, setEstimatePdf] = React.useState<File | null>(null)
  const [vinPresent, setVinPresent] = React.useState(false)
  const [odoPresent, setOdoPresent] = React.useState(false)
  const [damagePresent, setDamagePresent] = React.useState(false)

  React.useEffect(() => { loadPackets() }, [])

  function loadPackets() {
    setListLoading(true)
    fetch(api("/api/qc"), { headers: { "X-API-Key": API_KEY } })
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then((data) => { setPackets(data.items || []); setListLoading(false) })
      .catch(() => { setListLoading(false) })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!estimatePdf) return
    setLoading(true)
    setError("")
    setSuccess("")

    const form = new FormData()
    form.append("estimate_pdf", estimatePdf)
    form.append("vin_photo_present", String(vinPresent))
    form.append("odometer_photo_present", String(odoPresent))
    form.append("damage_photos_present", String(damagePresent))

    try {
      const res = await fetch(api("/api/qc"), {
        method: "POST",
        headers: { "X-API-Key": API_KEY },
        body: form,
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({} as any))
        throw new Error(data.detail || "HTTP " + res.status)
      }
      const data = await res.json()
      setSuccess("QC packet created: " + data.findings_count + " findings")
      setEstimatePdf(null)
      loadPackets()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <h2 className="mb-4 text-lg font-semibold text-[#c9d1d9]">Quality Control</h2>

      <div className="mb-6 rounded-lg border border-[#21262d] bg-[#161b22] p-6">
        <h3 className="mb-3 text-sm font-semibold text-[#c9d1d9]">Upload QC Packet</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs text-[#8b949e]">Estimate PDF</label>
            <input type="file" accept=".pdf" required onChange={(e) => setEstimatePdf(e.target.files?.[0] || null)}
              className="w-full rounded border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#58a6ff]" />
          </div>
          <div>
            <p className="mb-2 block text-xs text-[#8b949e]">Photo verification (check image PDF manually):</p>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={vinPresent} onChange={(e) => setVinPresent(e.target.checked)} className="h-4 w-4 rounded border-[#30363d] bg-[#0d1117] accent-[#f0883e]" />
                <span className="text-sm text-[#c9d1d9]">VIN photo present</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={odoPresent} onChange={(e) => setOdoPresent(e.target.checked)} className="h-4 w-4 rounded border-[#30363d] bg-[#0d1117] accent-[#f0883e]" />
                <span className="text-sm text-[#c9d1d9]">Odometer photo present</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={damagePresent} onChange={(e) => setDamagePresent(e.target.checked)} className="h-4 w-4 rounded border-[#30363d] bg-[#0d1117] accent-[#f0883e]" />
                <span className="text-sm text-[#c9d1d9]">Damage photos present</span>
              </label>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button type="submit" disabled={loading}
              className="inline-flex items-center gap-2 rounded border border-[#30363d] bg-[#21262d] px-4 py-2 text-sm text-[#c9d1d9] hover:bg-[#30363d] disabled:opacity-50">
              <Upload className="h-4 w-4" />
              {loading ? "Processing..." : "Run QC Review"}
            </button>
          </div>
        </form>
        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        {success && <p className="mt-3 text-sm text-green-400">{success}</p>}
      </div>

      <h3 className="mb-3 text-sm font-semibold text-[#c9d1d9]">QC Packets ({packets.length})</h3>
      {listLoading ? (
        <p className="text-sm text-[#8b949e]">Loading...</p>
      ) : packets.length === 0 ? (
        <p className="text-sm text-[#8b949e]">No QC packets yet.</p>
      ) : (
        <div className="space-y-2">
          {packets.map((p) => (
            <Link key={p.id} href={"/qc/" + p.id}
              className="flex items-center justify-between rounded-lg border border-[#21262d] bg-[#161b22] p-4 hover:border-[#30363d]">
              <div className="flex items-center gap-3">
                <ClipboardCheck className="h-5 w-5 text-[#484f58]" />
                <div>
                  <p className="text-sm font-medium text-[#c9d1d9]">{p.claim_number || "Untitled QC"}</p>
                  <p className="text-xs text-[#8b949e]">{p.vehicle || "Unknown vehicle"}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className={"rounded px-2 py-0.5 text-xs font-semibold " + (p.carrier_ready ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400")}>
                  {p.carrier_confidence_score}/100
                </span>
                <div className="flex items-center gap-1.5 text-[#8b949e]">
                  <span className="text-xs">{p.findings_count} findings</span>
                  <span className="text-xs text-[#484f58]">|</span>
                  <Clock className="h-3.5 w-3.5" />
                  <span className="text-xs">{formatDate(p.created_at)}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
