"use client"

import React, { useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2, Upload } from "lucide-react"

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "https://primoauditai-production.up.railway.app")
const API_KEY=*** || "pa_dev") as string

export default function AuditUploadPage() {
  const router = useRouter()
  const [estimatePdf, setEstimatePdf] = useState<File | null>(null)
  const [imagePdf, setImagePdf] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!estimatePdf) return

    setLoading(true)
    setError("")
    setStatus("Parsing estimate...")

    try {
      const form = new FormData()
      form.append("estimate_pdf", estimatePdf)
      if (imagePdf) form.append("image_pdf", imagePdf)
      form.append("vin_photo_present", "true")
      form.append("odometer_photo_present", "true")
      form.append("damage_photos_present", "true")

      setStatus("Extracting photos + running AI analysis...")
      const r = await fetch(`${API_URL}/api/qc`, {
        method: "POST",
        headers: { "X-API-Key": API_KEY },
        body: form,
      })

      if (!r.ok) {
        const err = await r.json()
        throw new Error(err.detail || `Upload failed (${r.status})`)
      }

      const data = await r.json()
      setStatus("Done! Redirecting...")
      router.push(`/audit/${data.id}`)
    } catch (err: any) {
      setError(err.message || "Upload failed")
      setLoading(false)
      setStatus("")
    }
  }

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#c9d1d9]">
      {/* Header */}
      <div className="border-b border-[#21262d] bg-[#161b22] px-4 py-3 flex items-center justify-between">
        <span className="text-sm font-semibold">PrimoAudit</span>
        <div className="text-[10px] text-[#484f58]">v3 · Unified Audit Engine</div>
      </div>

      <div className="mx-auto max-w-2xl px-4 py-12">
        <div className="mb-8 text-center">
          <h1 className="text-xl font-bold text-[#c9d1d9]">Run Audit</h1>
          <p className="mt-2 text-sm text-[#8b949e]">
            Upload a CCC estimate PDF and optional image PDF. The engine parses, extracts photos,
            runs 100+ rules, verifies findings with AI, and presents an audit-ready report.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Estimate PDF */}
          <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-6">
            <label className="mb-2 block text-sm font-semibold text-[#c9d1d9]">
              Estimate PDF <span className="text-[#f0883e]">*</span>
            </label>
            <p className="mb-3 text-xs text-[#8b949e]">CCC ONE estimate printout. Parsed for claim info, lines, panels, and metadata.</p>
            <div className="flex items-center gap-3">
              <label className="cursor-pointer rounded-lg border-2 border-dashed border-[#30363d] px-6 py-4 text-center transition-colors hover:border-[#58a6ff] hover:bg-[#1a1f2e]">
                <Upload className="mx-auto h-5 w-5 text-[#484f58]" />
                <span className="mt-1 block text-xs text-[#8b949e]">{estimatePdf ? estimatePdf.name : "Choose file..."}</span>
                <input type="file" accept=".pdf" required onChange={e => setEstimatePdf(e.target.files?.[0] || null)} className="hidden" />
              </label>
              {estimatePdf && <span className="text-xs text-green-400">✓ Ready</span>}
            </div>
          </div>

          {/* Image PDF */}
          <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-6">
            <label className="mb-2 block text-sm font-semibold text-[#c9d1d9]">
              Image PDF <span className="text-[#484f58] text-xs font-normal">— optional</span>
            </label>
            <p className="mb-3 text-xs text-[#8b949e]">Photo packet with damage images. Photos are extracted, analyzed by Gemini, and matched to estimate lines.</p>
            <div className="flex items-center gap-3">
              <label className="cursor-pointer rounded-lg border-2 border-dashed border-[#30363d] px-6 py-4 text-center transition-colors hover:border-[#58a6ff] hover:bg-[#1a1f2e]">
                <Upload className="mx-auto h-5 w-5 text-[#484f58]" />
                <span className="mt-1 block text-xs text-[#8b949e]">{imagePdf ? imagePdf.name : "Choose file..."}</span>
                <input type="file" accept=".pdf" onChange={e => setImagePdf(e.target.files?.[0] || null)} className="hidden" />
              </label>
              {imagePdf && <span className="text-xs text-green-400">✓ Ready</span>}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">{error}</div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !estimatePdf}
            className="w-full rounded-lg bg-[#1f6feb] px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#388bfd] disabled:cursor-not-allowed disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {status || "Processing..."}
              </>
            ) : (
              "Run Audit"
            )}
          </button>
          {loading && (
            <p className="text-center text-xs text-[#8b949e]">
              Parsing estimate · Extracting photos · Running 100+ rules · AI verification · Building report
            </p>
          )}
        </form>
      </div>
    </div>
  )
}
