"use client";
import React, { useState, useRef } from "react";
import { useAuditData } from "./AuditContext";
import { apiUrl } from "@/lib/api";

export const UploadHarness: React.FC = () => {
    const { setAuditRun } = useAuditData();
    
    const [emsZip, setEmsZip] = useState<File | null>(null);
    const [supportingFiles, setSupportingFiles] = useState<File[]>([]);
    const [evidenceMode, setEvidenceMode] = useState<'live'|'mock'|'live_with_fixtures'>('live');
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [pollMessage, setPollMessage] = useState<string | null>(null);
    
    const zipInputRef = useRef<HTMLInputElement>(null);
    const supportInputRef = useRef<HTMLInputElement>(null);

    const handleZipChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            setEmsZip(e.target.files[0]);
            setError(null);
        }
    };

    const handleSupportChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setSupportingFiles(prev => [...prev, ...Array.from(e.target.files!)]);
        }
    };

    const removeSupportFile = (idx: number) => {
        setSupportingFiles(prev => prev.filter((_, i) => i !== idx));
    };

    const loadDemoClaim = () => {
        const mockAudit = {
            audit_id: "demo_" + Math.random().toString(36).slice(2, 8),
            status: "completed",
            claim_package: {
                claim_number: "DEMO-2024-8842",
                carrier: "State Farm",
                vehicle: { year: 2020, make: "Toyota", model: "Camry", vin: "JTDBU4EE3B9123456" },
                shop: { name: "PrimoCollision Houston", shop_code: "PRM-HOU-01", address: "7820 Westheimer Rd" }
            },
            findings: [
                {
                    id: "f-1",
                    severity: "high",
                    category: "OEM Compliance",
                    description: "Aftermarket bumper cover (CAPA) used without carrier approval. Estimate line 4 specifies 'LKQ' but no documented authorization.",
                    confirmed: false,
                    overturned: false,
                    hermes_recommended_action: "review",
                    hermes_confidence_level: "high",
                    hermes_rationale_summary: "CAPA parts require explicit carrier authorization per policy language. No PAR or DRP waiver detected in claim docs.",
                    final_recommendation_text: "Request LKQ authorization via CCC workflow or escalate to desk reviewer. If denied, revise to OEM.",
                    advisory_tone: "assertive",
                    escalation_hint: "This shop has 3 prior CAPA flags in 90 days.",
                    action_playbook: {
                        primary: ["Pull shop profile from DMS", "Verify if CAPA waiver is on file", "If no waiver: request auth via CCC ONE", "Document response in notes"],
                        escalation_conditions: ["Shop refuses to provide waiver", "Carrier auto-denies CAPA for this YMM"],
                        guardrails: ["Do NOT overturn without DMS lookup", "Never approve CAPA on total loss claims"]
                    },
                    pattern_detection_flags: ["repeat_capa_usage", "shop_preference_mismatch"],
                    historical_signals: [{ type: "prior_flag", count: 3, time_window: "90d" }]
                },
                {
                    id: "f-2", 
                    severity: "medium",
                    category: "Diagnostic Time",
                    description: "2.5 hrs diagnostic labor on rear bumper — no visible structural damage in photos.",
                    confirmed: false,
                    overturned: false,
                    hermes_recommended_action: "dismiss",
                    hermes_confidence_level: "medium",
                    hermes_rationale_summary: "Photo evidence shows cosmetic scuff only. No frame/unibody involvement. 2.5 hrs exceeds carrier guideline of 0.5 hrs for visual inspection.",
                    final_recommendation_text: "Reduce to 0.5 hrs visual inspection or provide structural measurement report.",
                    advisory_tone: "neutral",
                    action_playbook: {
                        primary: ["Review uploaded photos for structural indicators", "Check if structural measurements attached", "If no measurements: request justification from estimator"],
                        escalation_conditions: ["Shop provides frame diagram showing deformation"],
                        guardrails: ["Do NOT dismiss without reviewing photos", "Always allow rebuttal with measurement data"]
                    }
                }
            ],
            scorecard: { 
                severity_tally: { high: 1, medium: 1, low: 0 }, 
                health_score: 72, 
                confirmation_rate: 0 
            },
            narrative: {
                summary: "2 findings flag potential overreach. CAPA auth gap is systemic concern given shop history.",
                key_risks: ["Carrier dispute on CAPA", "Customer complaint if delays from auth request"]
            },
            hermes_tasks: [
                { task: "Request CAPA authorization", priority: "urgent", assignee: "desk_reviewer" },
                { task: "Pull photo evidence for f-2", priority: "normal", assignee: "auditor" }
            ],
            advisory_banners: [
                { level: "critical", message: "Shop has repeat CAPA violations — consider DMP review", rule_reference: "POL-7821-C" }
            ],
            metadata: {
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                version: "1.0.0"
            }
        };
        setAuditRun(mockAudit);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!emsZip) { setError("Select an EMS ZIP payload."); return; }

        setIsUploading(true);
        setError(null);
        setPollMessage("Enqueuing job...");

        try {
            const formData = new FormData();
            formData.append("ems_zip", emsZip);
            formData.append("evidence_mode", evidenceMode);
            supportingFiles.forEach(f => formData.append("supporting_files", f));

            const res = await fetch(apiUrl("/api/audits"), { method: "POST", body: formData });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || `Server error: ${res.status}`);
            }

            const { audit_id } = await res.json();
            if (!audit_id) throw new Error("No audit_id returned from server");
            
            let status = "processing";
            let delay = 2000;
            const maxAttempts = 60;
            let attempts = 0;

            while (status === "processing" && attempts < maxAttempts) {
                await new Promise(r => setTimeout(r, delay));
                const pollRes = await fetch(apiUrl(`/api/audits/${audit_id}/status`));
                if (!pollRes.ok) throw new Error(`Status check failed: ${pollRes.status}`);
                const pollData = await pollRes.json();
                status = pollData.status;
                setPollMessage(`${pollData.message || "Processing..."} (${pollData.progress || 0}%)`);
                delay = Math.min(delay + 1000, 5000);
                attempts++;
            }

            if (status === "processing") throw new Error("Audit timed out after maximum attempts");
            if (status === "failed") throw new Error("Audit pipeline failed");

            setPollMessage("Loading results...");
            const finalRes = await fetch(apiUrl(`/api/audits/${audit_id}`));
            if (!finalRes.ok) throw new Error(`Failed to load finalized audit payload: ${finalRes.status}`);
            
            const auditData = await finalRes.json();
            setAuditRun(auditData);

        } catch (err: any) {
            console.error("Upload failed:", err);
            setError(err.message || "Failed to process claim");
        } finally {
            setIsUploading(false);
            setPollMessage(null);
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-slate-900 text-slate-200 font-sans p-6">
            <div className="max-w-xl w-full bg-slate-800 border border-slate-700 rounded-lg shadow-2xl p-8">
                <div className="text-center mb-10">
                    <h1 className="text-2xl font-black text-white tracking-widest uppercase mb-2">PrimoAudit AI</h1>
                    <p className="text-sm text-slate-400 font-bold uppercase tracking-widest">Local Testing Harness</p>
                </div>

                <div className="mb-6 p-4 bg-slate-700/50 border border-slate-600 rounded-lg">
                    <button 
                        onClick={loadDemoClaim}
                        disabled={isUploading}
                        className="w-full py-3 bg-emerald-700 hover:bg-emerald-600 disabled:bg-emerald-900 disabled:opacity-50 text-white font-bold rounded border border-emerald-500 transition-all"
                    >
                        🧪 Load Demo Claim (No Backend Required)
                    </button>
                    <p className="text-xs text-slate-500 mt-2 text-center">
                        Instantly loads realistic Hermes data with AI reasoning and playbooks
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-8">
                    <div className="space-y-3">
                        <label className="block text-[11px] font-black uppercase tracking-widest text-slate-400">1. EMS Claim Package (.zip)</label>
                        <div 
                            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${emsZip ? 'border-emerald-500 bg-emerald-500/10' : 'border-slate-600 hover:border-blue-500 hover:bg-slate-700/50'}`}
                            onClick={() => zipInputRef.current?.click()}
                        >
                            <input type="file" ref={zipInputRef} className="hidden" accept=".zip" onChange={handleZipChange} />
                            {emsZip ? (
                                <div className="flex items-center justify-center gap-3 text-emerald-400">
                                    <span className="text-2xl">📦</span>
                                    <span className="font-mono text-sm">{emsZip.name}</span>
                                </div>
                            ) : (
                                <div className="text-slate-400 flex flex-col items-center">
                                    <span className="text-2xl mb-2">📂</span>
                                    <span className="text-sm font-bold">Select EMS ZIP File</span>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <label className="block text-[11px] font-black uppercase tracking-widest text-slate-400">2. Supporting Evidence (Optional)</label>
                            <button type="button" onClick={() => supportInputRef.current?.click()} className="text-[10px] bg-slate-700 text-white px-2 py-1 rounded border border-slate-600 hover:bg-slate-600">
                                + Add Image/PDF
                            </button>
                        </div>
                        <input type="file" ref={supportInputRef} className="hidden" accept=".jpg,.jpeg,.png,.webp,.pdf" multiple onChange={handleSupportChange} />
                        {supportingFiles.length > 0 && (
                            <div className="bg-slate-900 border border-slate-700 rounded p-2 flex flex-col gap-1 max-h-40 overflow-y-auto">
                                {supportingFiles.map((f, idx) => (
                                    <div key={idx} className="flex items-center justify-between text-xs bg-slate-800 p-2 rounded border border-slate-700">
                                        <span className="font-mono truncate flex-1 text-slate-300">{f.name}</span>
                                        <button type="button" onClick={() => removeSupportFile(idx)} className="text-red-400 hover:text-red-300 px-2 font-bold">✕</button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="space-y-3">
                        <label className="block text-[11px] font-black uppercase tracking-widest text-slate-400">3. Extraction Mode</label>
                        <select 
                            value={evidenceMode}
                            onChange={(e) => setEvidenceMode(e.target.value as any)}
                            className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded p-3 font-mono focus:outline-none focus:border-blue-500"
                        >
                            <option value="live">Live (Strict Mode)</option>
                            <option value="live_with_fixtures">Live w/ Fallback Fixtures</option>
                            <option value="mock">Mock Override</option>
                        </select>
                        <p className="text-xs text-slate-500">
                            <strong>Mock</strong> = fixtures only, no AI call. <strong>Live w/ Fallback</strong> = tries AI, falls back. <strong>Live</strong> = must succeed.
                        </p>
                    </div>

                    <div className="pt-4 border-t border-slate-700">
                        {error && (
                            <div className="mb-4 bg-red-900/30 border border-red-800 text-red-400 p-3 rounded text-sm flex items-start gap-2">
                                <span>⚠️</span>
                                <span>{error}</span>
                            </div>
                        )}
                        {pollMessage && (
                            <div className="mb-4 bg-blue-900/30 border border-blue-800 text-blue-400 p-3 rounded text-sm text-center animate-pulse">
                                {pollMessage}
                            </div>
                        )}
                        <button 
                            type="submit" 
                            disabled={!emsZip || isUploading}
                            className={`w-full py-4 text-sm font-black uppercase tracking-widest rounded transition-all shadow-lg
                                ${!emsZip ? 'bg-slate-700 text-slate-500 cursor-not-allowed' 
                                : isUploading ? 'bg-blue-600 text-white animate-pulse' 
                                : 'bg-blue-600 hover:bg-blue-500 text-white hover:shadow-blue-500/20'}`}
                        >
                            {isUploading ? (pollMessage || 'Pipeline Running...') : 'Execute Audit Pipeline'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
