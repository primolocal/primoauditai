"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Upload, FileText, AlertCircle, Loader2 } from "lucide-react"
import { Button } from "../components/ui/button"
import { cn } from "../lib/utils"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API_KEY = "pa_dev_key"

export default function UploadPage() {
  const router = useRouter()
  const [file, setFile] = React.useState<File | null>(null)
  const [dragOver, setDragOver] = React.useState(false)
  const [uploading, setUploading] = React.useState(false)
  const [error, setError] = React.useState("")
  const [fields, setFields] = React.useState({
    claim_number: "",
    vehicle_year: "",
    vehicle_make: "",
    vehicle_model: "",
    insurance_company: "",
  })

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }
  const onDragLeave = () => setDragOver(false)
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f && (f.name.endsWith(".pdf") || f.name.endsWith(".zip"))) {
      setFile(f)
      setError("")
    } else {
      setError("Only PDF or ZIP files allowed")
    }
  }

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      setError("")
    }
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setError("Select a PDF or ZIP file")
      return
    }
    setUploading(true)
    setError("")

    const form = new FormData()
    form.append("estimate_pdf", file)
    Object.entries(fields).forEach(([k, v]) => {
      if (v) form.append(k, v)
    })

    try {
      const res = await fetch(`${API_URL}/api/audits`, {
        method: "POST",
        headers: { "X-API-Key": API_KEY },
        body: form,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Upload failed: ${res.status}`)
      }
      const data = await res.json()
      router.push(`/audit/${data.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h2 className="mb-6 text-lg font-semibold text-[#c9d1d9]">Upload Estimate</h2>

      {/* Drop zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={cn(
          "mb-6 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
          dragOver
            ? "border-[#f0883e] bg-[#f0883e]/5"
            : "border-[#30363d] bg-[#161b22] hover:border-[#484f58]"
        )}
      >
        <Upload className="mx-auto mb-3 h-10 w-10 text-[#484f58]" />
        <p className="mb-2 text-sm text-[#8b949e]">
          Drag & drop a PDF or ZIP here, or{" "}
          <label className="cursor-pointer text-[#f0883e] hover:underline">
            browse
            <input
              type="file"
              accept=".pdf,.zip"
              className="sr-only"
              onChange={onFileChange}
            />
          </label>
        </p>
        {file && (
          <div className="mt-3 flex items-center justify-center gap-2 text-sm text-[#c9d1d9]">
            <FileText className="h-4 w-4 text-[#f0883e]" />
            <span>{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
          </div>
        )}
      </div>

      {/* Form fields */}
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-[#8b949e]">Claim #</label>
            <input
              value={fields.claim_number}
              onChange={(e) => setFields({ ...fields, claim_number: e.target.value })}
              className="w-full rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#f0883e]"
              placeholder="CLM-12345"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#8b949e]">Vehicle Year</label>
            <input
              value={fields.vehicle_year}
              onChange={(e) => setFields({ ...fields, vehicle_year: e.target.value })}
              className="w-full rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#f0883e]"
              placeholder="2024"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#8b949e]">Make</label>
            <input
              value={fields.vehicle_make}
              onChange={(e) => setFields({ ...fields, vehicle_make: e.target.value })}
              className="w-full rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#f0883e]"
              placeholder="Toyota"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-[#8b949e]">Model</label>
            <input
              value={fields.vehicle_model}
              onChange={(e) => setFields({ ...fields, vehicle_model: e.target.value })}
              className="w-full rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#f0883e]"
              placeholder="Camry"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-[#8b949e]">Insurance Company</label>
          <input
            value={fields.insurance_company}
            onChange={(e) => setFields({ ...fields, insurance_company: e.target.value })}
            className="w-full rounded-md border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#c9d1d9] outline-none focus:border-[#f0883e]"
            placeholder="Nationwide"
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-md bg-red-500/10 p-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        <div className="flex justify-end">
          <Button type="submit" disabled={uploading || !file}>
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              "Run Audit"
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
// 1780928986
