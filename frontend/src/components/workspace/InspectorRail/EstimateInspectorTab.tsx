"use client";
import React, { useEffect, useRef } from "react";
import { useAuditData } from "../AuditContext";

export const EstimateInspectorTab: React.FC = () => {
    const { auditRun, selectedFinding } = useAuditData();
    const scrollRef = useRef<HTMLTableRowElement | null>(null);
    
    const lines = auditRun?.estimate_lines.items || [];
    const affectedLines = selectedFinding?.affected_lines || [];
    const activeSupplement = auditRun?.active_supplement || "E01";

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [selectedFinding]);
    
    const firstAffectedIndex = lines.findIndex(l => affectedLines.includes(l.line_no));

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center mb-2 pb-1 border-b border-slate-200">
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                    Line Items Filter
                </div>
                <div className="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded border bg-blue-50 border-blue-200 text-blue-700 shadow-sm">
                    {activeSupplement} ACTIVE
                </div>
            </div>
            
            <div className="flex items-center gap-3 text-[9px] font-black uppercase tracking-widest mb-2 text-slate-500">
                <div className="flex items-center gap-1"><span className="text-emerald-700 bg-emerald-100 px-1 rounded">+</span> Added</div>
                <div className="flex items-center gap-1"><span className="text-amber-700 bg-amber-100 px-1 rounded">~</span> Modified</div>
                <div className="flex items-center gap-1 opacity-50"><span className="text-slate-500 bg-slate-200 px-1 rounded"> </span> Legacy</div>
            </div>

            <div className="bg-white border border-slate-200 shadow-sm rounded-lg overflow-hidden relative custom-scrollbar">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-slate-50 text-[9px] uppercase tracking-widest text-slate-500 font-bold border-b border-slate-200">
                            <th className="p-2 w-16 whitespace-nowrap">Line</th>
                            <th className="p-2">Description</th>
                            <th className="p-2 text-center w-16">Labor</th>
                            <th className="p-2 text-right w-20">Amt</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lines.map((l, i) => {
                            const isAffected = affectedLines.includes(l.line_no);
                            const isAdded = l.delta_status === 'added';
                            const isModified = l.delta_status === 'modified';
                            const isOriginal = l.delta_status === 'original' || l.delta_status === 'unchanged';
                            
                            let rowClasses = "text-[10px] border-b border-slate-100 last:border-0 relative transition-colors ";
                            
                            if (isAffected) {
                                rowClasses += "bg-blue-50 text-blue-800 font-bold ring-1 ring-inset ring-blue-300 z-10 ";
                            } else {
                                if (isAdded) rowClasses += "bg-emerald-50/50 text-emerald-800 hover:bg-emerald-50 ";
                                else if (isModified) rowClasses += "bg-amber-50/50 text-amber-800 hover:bg-amber-50 ";
                                else rowClasses += "text-slate-500 hover:bg-slate-50 hover:text-slate-700 opacity-70 ";
                            }

                            return (
                                <tr key={i} ref={i === firstAffectedIndex ? scrollRef : null} className={rowClasses}>
                                    {isAffected && <td className="absolute left-0 top-0 w-1 h-full bg-blue-500 shadow-[2px_0_5px_rgba(59,130,246,0.3)]" />}
                                    <td className="p-2 border-r border-slate-100 font-mono flex items-center gap-1.5">
                                        L{l.line_no}
                                        {isAdded && !isAffected && <span className="text-[8px] bg-emerald-100 text-emerald-700 px-0.5 rounded leading-none">+</span>}
                                        {isModified && !isAffected && <span className="text-[8px] bg-amber-100 text-amber-700 px-0.5 rounded leading-none">~</span>}
                                    </td>
                                    <td className="p-2 border-r border-slate-100 truncate max-w-[120px]" title={l.description}>{l.description}</td>
                                    <td className="p-2 border-r border-slate-100 font-mono text-center opacity-80">{l.labor_hours > 0 ? l.labor_hours.toFixed(1) : '-'}</td>
                                    <td className="p-2 font-mono text-right opacity-80">${(l.price + l.sublet_amount).toFixed(2)}</td>
                                </tr>
                            );
                        })}
                        {lines.length === 0 && (
                            <tr><td colSpan={4} className="p-4 text-center text-xs text-slate-500">No lines parsed.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
