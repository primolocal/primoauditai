"use client";
import React, { useState, useCallback } from "react";

interface Finding {
  severity: string;
  summary: string;
  lines: number[];
}

interface QCResult {
  audit_id: string;
  claim_number: string;
  file_type: string;
  is_supplement: boolean;
  vehicle: { year?: number; make?: string; model?: string; mileage?: number; vin?: string };
  shop: { name?: string; state?: string };
  findings: Record<string, Finding[]>;
  total_findings: number;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-700 text-red-100 border-red-500",
  high: "bg-red-900/50 text-red-300 border-red-700",
  medium: "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  low: "bg-slate-800 text-slate-300 border-slate-600",
};

const CAT_LABELS: Record<string, { label: string; icon: string }> = {
  state: { label: "STATE COMPLIANCE", icon: "⚖️" },
  remove: { label: "MUST REMOVE", icon: "❌" },
  fix: { label: "MUST FIX", icon: "✏️" },
  verify: { label: "MUST VERIFY", icon: "📋" },
  attach: { label: "MUST ATTACH", icon: "📎" },
  review: { label: "REVIEW", icon: "🔍" },
};

export default function QCContent() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QCResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("estimate_pdf", file);
      const res = await fetch("/api/qc", { method: "POST", body: form });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [file]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-mono text-sm">
      <div className="border-b border-slate-800 px-6 py-4">
        <h1 className="text-xl font-bold text-amber-400">PrimoAuditAI QC Report</h1>
        <p className="text-slate-500 text-xs mt-1">Upload estimate PDF or CCC ZIP — instant compliance check</p>
      </div>

      <div className="px-6 py-6 border-b border-slate-800">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-xs text-slate-400 mb-2">Estimate PDF or CCC ZIP</label>
            <input
              type="file"
              accept=".pdf,.zip"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-slate-300 file:mr-4 file:py-2 file:px-4 file:bg-slate-800 file:text-amber-400 file:border file:border-slate-700 file:rounded file:cursor-pointer"
            />
          </div>
          <button
            onClick={handleUpload}
            disabled={!file || loading}
            className="px-6 py-2 bg-amber-600 text-black font-bold rounded disabled:opacity-30 disabled:cursor-not-allowed hover:bg-amber-500 transition"
          >
            {loading ? "ANALYZING..." : "RUN QC"}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-3">Error: {error}</p>}
      </div>

      {result && (
        <div className="px-6 py-6">
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 mb-6">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg text-white font-bold">
                  {result.is_supplement ? "SUPPLEMENT" : "ESTIMATE"} QC: {result.claim_number}
                </h2>
                <p className="text-slate-400 text-xs mt-1">
                  {result.vehicle.year} {result.vehicle.make} {result.vehicle.model?.slice(0, 40)}
                  {result.vehicle.mileage ? ` | ${result.vehicle.mileage.toLocaleString()} mi` : ""}
                  {result.shop.state ? ` | ${result.shop.state}` : ""}
                </p>
                {result.shop.name && (
                  <p className="text-slate-500 text-xs">Shop: {result.shop.name}</p>
                )}
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold text-amber-400">{result.total_findings}</span>
                <p className="text-slate-500 text-xs">findings</p>
              </div>
            </div>
          </div>

          {Object.entries(CAT_LABELS).map(([cat, { label, icon }]) => {
            const items = result.findings[cat];
            if (!items || items.length === 0) return null;
            return (
              <div key={cat} className="mb-6">
                <h3 className="text-sm font-bold text-slate-300 mb-3 border-b border-slate-800 pb-2">
                  {icon} {label} ({items.length})
                </h3>
                <div className="space-y-2">
                  {items.map((f, i) => (
                    <div
                      key={i}
                      className={`border rounded px-4 py-3 ${SEVERITY_COLORS[f.severity] || SEVERITY_COLORS.low}`}
                    >
                      <div className="flex gap-3">
                        {f.lines.length > 0 && f.lines[0] && (
                          <span className="text-xs font-bold text-amber-400 shrink-0 mt-0.5">
                            L{f.lines.join(", ")}
                          </span>
                        )}
                        <div>
                          <p className="text-xs">{f.summary}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
