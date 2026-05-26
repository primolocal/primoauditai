"use client";

import React, { useState } from "react";
import { useAuditData, useAuditInteraction } from "../AuditContext";
import { Finding } from "@/types/claim";
import { apiUrl } from "@/lib/api";

export const NarrativeInspectorTab: React.FC = () => {
    const { auditRun, selectedFinding } = useAuditData();
    const narrative = auditRun?.narrative;

    let fullText = "Awaiting narrative generation...";
    if (narrative) {
        const sections = [
            narrative.damage_summary,
            narrative.claim_summary,
            narrative.reviewer_notes,
            narrative.escalation_note
        ].filter(Boolean);
        fullText = sections.join("\n\n");
    }

    if (selectedFinding && selectedFinding.status !== "overturned") {
         fullText = `--- TARGET FINDING OVERRIDE ([${selectedFinding.rule_id}]) ---\n` +
                    `Flagged: ${selectedFinding.message}\n` +
                    `Auditor Directive: ${selectedFinding.recommended_action}\n` +
                    `-------------------------------------------------\n\n` +
                    fullText;
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center mb-2 pb-1 border-b border-slate-200">
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                    Generated Narrative
                </div>
                {auditRun?.active_supplement && auditRun.active_supplement !== "E01" && (
                    <div className="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded border border-purple-200 bg-purple-50 text-purple-700">
                        {auditRun.active_supplement} SCOPE
                    </div>
                )}
            </div>
            
            <textarea 
                className="w-full h-80 bg-slate-50 border border-slate-300 rounded p-3 text-xs text-slate-800 resize-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 outline-none leading-relaxed transition-all shadow-sm custom-scrollbar"
                value={fullText}
                readOnly
            />
            
            <div className="flex gap-2 mt-2">
                <button className="flex-1 bg-white border border-slate-300 hover:bg-slate-50 hover:text-slate-900 active:scale-95 py-2 rounded text-[10px] uppercase font-black tracking-widest text-slate-600 transition-all shadow-sm">Regenerate</button>
                <button className="flex-1 bg-white border border-slate-300 hover:bg-slate-50 hover:text-slate-900 active:scale-95 py-2 rounded text-[10px] uppercase font-black tracking-widest text-slate-600 transition-all shadow-sm">Copy Markdown</button>
            </div>
        </div>
    );
};

export const ReviewerActionTab: React.FC = () => {
    const { auditRun, setAuditRun } = useAuditData();
    const { selectedFindingId } = useAuditInteraction();
    const [reason, setReason] = useState("");
    const [comment, setComment] = useState("");

    const handleAction = async (action: 'confirm' | 'overturn') => {
        if (!auditRun || !selectedFindingId) return;
        try {
            const body = { reason_code: reason, comment: comment };
            const res = await fetch(apiUrl(`/audits/${auditRun.run_id}/findings/${selectedFindingId}/${action}`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (res.ok) {
                const data = await res.json();
                const updatedRun = {
                    ...auditRun,
                    scorecard: data.scorecard,
                    narrative: data.narrative,
                    findings: auditRun.findings.map((f: Finding) => f.id === selectedFindingId ? data.finding : f),
                    status: data.status,
                    blockers: data.blockers,
                    activity_log: data.activity_log
                };
                setAuditRun(updatedRun);
                setReason("");
                setComment("");
            }
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="space-y-6">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 pb-1 border-b border-slate-200">
                Disarm / Escalate Finding
            </div>
            
            <div className="flex flex-col gap-3">
                <button onClick={() => handleAction('confirm')} className="w-full bg-emerald-600 hover:bg-emerald-700 border border-emerald-700 text-white py-3 rounded text-[10px] font-black uppercase tracking-widest shadow-sm transition-all active:scale-[0.98]">
                    Confirm Finding
                </button>
                <button onClick={() => handleAction('overturn')} className="w-full bg-white hover:bg-slate-50 border border-slate-300 hover:text-slate-900 text-slate-700 py-3 rounded text-[10px] font-black uppercase tracking-widest shadow-sm transition-all active:scale-[0.98]">
                    Overturn Finding
                </button>
            </div>

            <div className="flex flex-col gap-3 mt-6">
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">Override Reason</div>
                <select 
                    className="bg-white border border-slate-300 text-slate-800 shadow-sm text-xs rounded p-2.5 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 transition-all"
                    value={reason} onChange={e => setReason(e.target.value)}
                >
                    <option value="">Select formal reason...</option>
                    <option value="carrier_exception">Carrier exception on file</option>
                    <option value="evidence_miscategorized">Evidence mis-categorized by AI</option>
                    <option value="false_positive">False Positive Rule Trigger</option>
                </select>

                <textarea 
                    placeholder="Internal audit trail comment..."
                    className="w-full h-24 bg-white border border-slate-300 shadow-sm rounded p-3 text-xs text-slate-800 resize-none outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 transition-all custom-scrollbar"
                    value={comment} onChange={e => setComment(e.target.value)}
                />

                <div className="flex items-center gap-2 mt-2">
                    <input type="checkbox" id="train" className="rounded border-slate-300 bg-white" />
                    <label htmlFor="train" className="text-xs text-slate-600 cursor-pointer">Flag to train Rules Engine</label>
                </div>
            </div>
        </div>
    );
};
