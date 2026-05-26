"use client";
import React from "react";
import { useAuditData } from "../AuditContext";

export const IngestionStatusCard: React.FC = () => {
    const { auditRun } = useAuditData();
    if (!auditRun) return null;

    return (
        <div className="bg-white border border-slate-200 shadow-sm rounded-lg p-4">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 border-b border-slate-100 pb-1">
                Package Status
            </div>
            
            <div className="space-y-1.5 mt-2">
                <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 font-bold uppercase tracking-wider text-[9px]">Upload Source</span>
                    <span className="text-blue-600 font-mono">{auditRun.claim_package?.carrier || "Unknown Source"}</span>
                </div>
                
                <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 font-bold uppercase tracking-wider text-[9px]">EMS Status</span>
                    <span className="text-emerald-600 font-bold text-[10px] uppercase">Verified</span>
                </div>

                <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 font-bold uppercase tracking-wider text-[9px]">Extraction</span>
                    <span className="text-emerald-600 font-bold text-[10px] uppercase">Success</span>
                </div>
                
                <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-slate-100">
                    <div className="bg-slate-50 border border-slate-100 rounded p-1.5 flex justify-between items-center">
                        <span className="text-[9px] uppercase font-bold text-slate-500">PDFs</span>
                        <span className="text-xs font-mono font-bold text-slate-700">2</span>
                    </div>
                    <div className="bg-slate-50 border border-slate-100 rounded p-1.5 flex justify-between items-center">
                        <span className="text-[9px] uppercase font-bold text-slate-500">Photos</span>
                        <span className="text-xs font-mono font-bold text-slate-700">18</span>
                    </div>
                </div>

                <div className="text-[9px] uppercase tracking-widest text-slate-500 mt-2 bg-slate-50 border border-slate-100 px-2 py-1 flex items-center justify-between rounded">
                    <span>Missing Docs</span>
                    <span className="text-red-500 font-bold">Prior Auth PDF</span>
                </div>
                
                <div className="text-[9px] uppercase tracking-widest text-slate-500 bg-slate-50 border border-slate-100 px-2 py-1 flex items-center justify-between rounded mt-1">
                    <span>Shop Detected</span>
                    <span className="text-emerald-600 font-bold text-xs">Yes</span>
                </div>
            </div>
        </div>
    );
};
