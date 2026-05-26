"use client";
import React from "react";
import { useAuditData } from "../AuditContext";

export const ClaimSignalsCard: React.FC = () => {
    const { auditRun } = useAuditData();
    if (!auditRun) return null;

    // Hardcoded for mock, normally driven by EvidenceMatrix or RulesModule
    const flags = [
        { label: "Missing Prod Photo", active: true, color: "bg-red-50 text-red-700 border-red-200" },
        { label: "PDR Present", active: true, color: "bg-amber-50 text-amber-700 border-amber-200" },
        { label: "Possible UPD", active: true, color: "bg-amber-50 text-amber-700 border-amber-200" },
        { label: "Repaired Before Insp", active: false, color: "" },
        { label: "Shop Photos Only", active: true, color: "bg-blue-50 text-blue-700 border-blue-200" },
        { label: "TL Risk (12%)", active: true, color: "bg-slate-50 text-slate-500 border-slate-200" },
    ];

    return (
        <div className="bg-white border border-slate-200 shadow-sm rounded-lg p-4">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3 border-b border-slate-100 pb-1 flex justify-between items-center">
                <span>Claim Signals</span>
                <span className="text-[8px] bg-red-50 text-red-600 border border-red-100 px-1.5 py-0.5 rounded">AI SCANNED</span>
            </div>
            
            <div className="flex flex-wrap gap-2">
                {flags.filter(f => f.active).map(f => (
                    <span key={f.label} className={`px-2 py-1 rounded text-[9px] uppercase font-bold tracking-widest border border-dashed ${f.color}`}>
                        {f.label}
                    </span>
                ))}
            </div>
        </div>
    );
};
