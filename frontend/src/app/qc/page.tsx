"use client"

import * as React from "react"
import Link from "next/link"
import { ClipboardCheck, Clock, Upload } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API_KEY = "pa_dev_key"

interface QCPacket {
  id: string
  claim_number: string | null
  vehicle: string | null
  status: string
  findings_count: number
  photo_total: number
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
  const [imagePdf, setImagePdf] = React.useState<File | null>(null)

  React.useEffect(() => {
    loadPackets()
  }, [])

  function loadPackets() {
    setListLoading(true)
    fetch(`${API_URL}/api/qc`, { headers: { "X-API-Key": API_KEY } })
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then((data) => {
        setPackets(data.items || [])
        setListLoading(false)
      })
      .catch((err) => {
        setListLoading(false)
      })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!estimatePdf || !imagePdf) return
    setLoading(true)
    setError("")
    setSuccess("")

    const form = new FormData()
    form.append("estimate_pdf", estimatePdf)
    form.append("image_pdf", imagePdf)

    try {
      const res = await fetch(`${API_URL}/api/qc`, {
        method: "POST",
        headers: { "X-API-Key": API_KEY },
        body: form,
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setSuccess(`QC packet created: ${data.findings_count} findings, ${data.photo_total} photos`)
      setEstimatePdf(null)
      setImagePdf(null)
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

      {/* Upload section */}
      <div className="mb-6 rounded-lg border border-[#21262d] bg-[#161b22] p-6">
        <h3 className="mb-3 text-sm font-semibold text-[#c9d1d9]">Upload QC Packet</h3>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs text-[#8b949e]">Estimate PDF</label>
            <input
              type="file"
              accept=".pdf"
              required
              onChange={(e) => setEstimatePdf(e.target.files?.[0] || null)}
              className="w-full rounded border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#58a6ff]"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[#8b949e]">Image Packet PDF</label>
            <input
              type="file"
              accept=".pdf"
              required
              onChange={(e) => setImagePdf(e.target.files?.[0] || null)}
              className="w-full rounded border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#58a6ff]"
            />
          </div>
          <div className="col-span-full flex items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 rounded border border-[#30363d] bg-[#21262d] px-4 py-2 text-sm text-[#c9d1d9] hover:bg-[#30363d] disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              {loading ? "Processing..." : "Run QC Review"}
            </button>
            {estimatePdf && <span className="text-xs text-green-400">✓ {estimatePdf.name}</span>}
            {imagePdf && <span className="text-xs text-green-400">✓ {imagePdf.name}</span>}
          </div>
        </form>

        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        {success && <p className="mt-3 text-sm text-green-400">{success}</p>}
      </div>

      {/* Packets list */}
      <h3 className="mb-3 text-sm font-semibold text-[#c9d1d9]">QC Packets ({packets.length})</h3>

      {listLoading ? (
        <p className="text-sm text-[#8b949e]">Loading...</p>
      ) : packets.length === 0 ? (
        <p className="text-sm text-[#8b949e]">No QC packets yet.</p>
      ) : (
        <div className="space-y-2">
          {packets.map((p) => (
            <Link
              key={p.id}
              href={`/qc/${p.id}`}
              className="flex items-center justify-between rounded-lg border border-[#21262d] bg-[#161b22] p-4 hover:border-[#30363d]"
            >
              <div className="flex items-center gap-3">
                <ClipboardCheck className="h-5 w-5 text-[#484f58]" />
                <div>
                  <p className="text-sm font-medium text-[#c9d1d9]">
                    {p.claim_number || "Untitled QC"}
                  </p>
                  <p className="text-xs text-[#8b949e]">{p.vehicle || "Unknown vehicle"}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-[#8b949e]">
                    {p.findings_count} findings
                  </span>
                  <span className="text-xs text-[#484f58]">| {p.photo_total} photos</span>
                </div>
                <div className="flex items-center gap-1.5 text-[#484f58]">
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
