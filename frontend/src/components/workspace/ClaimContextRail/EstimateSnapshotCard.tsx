"use client";
import React from "react";
import { useAuditData } from "../AuditContext";

export const EstimateSnapshotCard: React.FC = () => {
    const { auditRun } = useAuditData();
    if (!auditRun) return null;

    const t = auditRun.estimate_lines.totals;
    const computedLaborHours = auditRun.estimate_lines.items.reduce((sum, item) => sum + (item.labor_hours || 0), 0);
    const computedPaintHours = auditRun.estimate_lines.items.reduce((sum, item) => sum + (item.paint_hours || 0), 0);

    return (
        <div className="bg-white border border-slate-200 shadow-sm rounded-lg p-4">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 border-b border-slate-100 pb-1">
                Estimate Snapshot
            </div>
            
            {!t ? (
                <div className="italic text-slate-500 text-center p-6 border border-dashed border-slate-300 rounded bg-slate-50 text-xs mt-2">
                    No estimate values available
                </div>
            ) : (
                <>
            
            <div className="flex flex-col mb-3 mt-2 items-center">
                <span className="text-xs uppercase font-bold tracking-widest text-slate-500 mb-0.5">Gross Total</span>
                <span className="text-xl font-black text-red-600 leading-none">${t?.gross_total.toFixed(2)}</span>
            </div>

            <div className="grid grid-cols-2 gap-x-2 gap-y-1.5 mt-2">
                <div className="flex justify-between items-center border-b border-dashed border-slate-200 pb-1">
                    <span className="text-[9px] text-slate-500 uppercase font-black">Labor ($)</span>
                    <span className="text-xs font-mono text-slate-800">${t?.total_labor.toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center border-b border-dashed border-slate-200 pb-1">
                    <span className="text-[9px] text-slate-500 uppercase font-black">Parts ($)</span>
                    <span className="text-xs font-mono text-slate-800">${t?.total_parts.toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center border-b border-dashed border-slate-200 pb-1 col-span-2">
                    <span className="text-[9px] text-slate-500 uppercase font-black">Labor Hours</span>
                    <span className="text-xs font-mono text-slate-800">{computedLaborHours.toFixed(1)} hrs</span>
                </div>
                <div className="flex justify-between items-center border-b border-dashed border-slate-200 pb-1 col-span-2">
                    <span className="text-[9px] text-slate-500 uppercase font-black">Paint Hours</span>
                    <span className="text-xs font-mono text-slate-800">{computedPaintHours.toFixed(1)} hrs</span>
                </div>
                <div className="flex justify-between items-center pb-1">
                    <span className="text-[9px] text-slate-500 uppercase font-black">Supplements</span>
                    <span className="text-xs font-mono font-bold text-amber-600">1</span>
                </div>
            </div>
            </>
            )}
        </div>
    );
};
