"use client";
import React, { useEffect, useState } from "react";
import { useAuditData } from "../AuditContext";
import { API_BASE } from "@/lib/api";
import { ChevronDown, ChevronUp, History, ShieldAlert, CheckCircle, AlertTriangle } from "lucide-react";

export const ClaimHistoryCard: React.FC = () => {
    const { auditRun } = useAuditData();
    const [history, setHistory] = useState<any>(null);
    const [expanded, setExpanded] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!auditRun || !auditRun.claim_package?.claim_number) {
            setLoading(false);
            return;
        }

        const fetchHistory = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/claims/${auditRun.claim_package.claim_number}/history`);
                if (res.ok) {
                    const data = await res.json();
                    setHistory(data);
                }
            } catch (err) {
                console.error("Failed to fetch claim history", err);
            } finally {
                setLoading(false);
            }
        };

        fetchHistory();
    }, [auditRun]);

    if (!auditRun) return null;
    if (loading) return (
        <div className="bg-white border border-slate-200 shadow-sm rounded-lg p-4 animate-pulse">
            <div className="h-4 bg-slate-200 rounded w-1/3 mb-2"></div>
            <div className="h-4 bg-slate-200 rounded w-full"></div>
        </div>
    );

    if (!history || history.prior_audit_count === 0) {
        return (
            <div className="bg-white border border-slate-200 shadow-sm rounded-lg p-3 flex justify-between items-center opacity-70">
                <span className="text-[10px] uppercase font-bold text-slate-400 flex items-center gap-1.5"><History className="w-3.5 h-3.5" /> No Claim History</span>
                <span className="text-[9px] uppercase tracking-widest bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">NEW CLAIM</span>
            </div>
        );
    }

    return (
        <div className="bg-white border border-indigo-200 shadow-sm rounded-lg flex flex-col overflow-hidden">
            <div 
                className="w-full bg-indigo-50 hover:bg-indigo-100 cursor-pointer p-3 flex justify-between items-center transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-2">
                    <History className="w-4 h-4 text-indigo-600" />
                    <span className="text-xs font-black uppercase text-indigo-900 tracking-widest">Prior History Map</span>
                </div>
                <div className="flex gap-2 items-center">
                    {history.risk_flags && history.risk_flags.length > 0 && (
                        <span className="flex items-center gap-1 text-[9px] font-bold bg-rose-100 text-rose-700 px-1.5 py-[1px] rounded uppercase border border-rose-200">
                            <ShieldAlert className="w-3 h-3" /> RISK DETECTED
                        </span>
                    )}
                    <span className="text-[10px] font-bold bg-indigo-200 text-indigo-800 px-1.5 py-[1px] rounded uppercase">{history.prior_audit_count} Events</span>
                    {expanded ? <ChevronUp className="w-4 h-4 text-indigo-500" /> : <ChevronDown className="w-4 h-4 text-indigo-500" />}
                </div>
            </div>

            {expanded && (
                <div className="p-4 flex flex-col gap-4 border-t border-indigo-100 bg-white">
                    {/* Risk Flags Explicit Warnings */}
                    {history.risk_flags && history.risk_flags.length > 0 && (
                        <div className="flex flex-col gap-1.5 mb-1">
                            {history.risk_flags.includes("high_revision_claim") && (
                                <div className="bg-rose-50 text-rose-800 text-[10px] uppercase font-bold tracking-widest px-2 py-1.5 rounded border border-rose-200 flex items-center gap-2">
                                    <AlertTriangle className="w-3 h-3 text-rose-600" /> High Revision History
                                </div>
                            )}
                            {history.risk_flags.includes("high_overturn_rate") && (
                                <div className="bg-rose-50 text-rose-800 text-[10px] uppercase font-bold tracking-widest px-2 py-1.5 rounded border border-rose-200 flex items-center gap-2">
                                    <ShieldAlert className="w-3 h-3 text-rose-600" /> High System Overturn Rate
                                </div>
                            )}
                            {history.risk_flags.includes("recommendation_risk") && (
                                <div className="bg-amber-50 text-amber-800 text-[10px] uppercase font-bold tracking-widest px-2 py-1.5 rounded border border-amber-200 flex items-center gap-2">
                                    <AlertTriangle className="w-3 h-3 text-amber-600" /> History of Aggressive Actions
                                </div>
                            )}
                        </div>
                    )}
                    {/* Indicators Section */}
                    <div className="grid grid-cols-2 gap-2 mb-2">
                        {history.indicators.previously_validated > 0 && (
                            <div className="flex items-start gap-1.5 bg-emerald-50 border border-emerald-100 p-2 rounded">
                                <CheckCircle className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                                <div className="text-[9px] uppercase font-bold text-emerald-800 leading-tight">Previously<br/>Validated</div>
                            </div>
                        )}
                        {history.indicators.previously_overturned > 0 && (
                            <div className="flex items-start gap-1.5 bg-rose-50 border border-rose-100 p-2 rounded">
                                <ShieldAlert className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
                                <div className="text-[9px] uppercase font-bold text-rose-800 leading-tight">Logic<br/>Overturned</div>
                            </div>
                        )}
                        {history.indicators.recommendation_too_aggressive > 0 && (
                            <div className="flex items-start gap-1.5 bg-amber-50 border border-amber-100 p-2 rounded">
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                                <div className="text-[9px] uppercase font-bold text-amber-800 leading-tight">Action Too<br/>Aggressive</div>
                            </div>
                        )}
                        {/* Always show revision count if valid */}
                        {(history.prior_revision_count > 0 || history.prior_audit_count > 1) && (
                            <div className="flex items-start gap-1.5 bg-blue-50 border border-blue-100 p-2 rounded">
                                <span className="text-[9px] uppercase font-bold text-blue-800 leading-tight flex flex-col">
                                    <span className="text-blue-500">{history.prior_revision_count > 0 ? history.prior_revision_count : history.prior_audit_count}</span>
                                    {history.prior_revision_count > 0 ? 'Prior Revisions' : 'Supplements'}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Timeline List */}
                    <div className="flex flex-col gap-0 relative isolate">
                        <div className="absolute left-2.5 top-2 bottom-2 w-px bg-slate-200 -z-10" />
                        {history.timeline.map((event: any, idx: number) => (
                            <div key={idx} className="flex gap-3 relative z-10 py-2">
                                <div className="w-5 h-5 rounded-full bg-slate-50 border-2 border-slate-300 shrink-0 flex items-center justify-center mt-0.5">
                                    <div className="w-2 h-2 rounded-full bg-slate-400" />
                                </div>
                                <div className="flex flex-col flex-1 pb-2">
                                    <div className="flex justify-between items-baseline mb-1">
                                        <span className="text-[10px] font-black uppercase text-slate-700">{event.event}</span>
                                        <span className="text-[9px] font-mono text-slate-400">{new Date(event.date).toLocaleDateString()}</span>
                                    </div>
                                    <div className="text-[9px] uppercase font-bold tracking-widest text-slate-500 bg-slate-50 p-1.5 rounded border border-slate-100 flex gap-2 w-max">
                                        <span>{event.findings_count} Findings</span>
                                        {event.truth_summary.validated > 0 && <span className="text-emerald-600 border-l border-slate-200 pl-2">+{event.truth_summary.validated} Valid</span>}
                                        {event.truth_summary.overturned > 0 && <span className="text-rose-600 border-l border-slate-200 pl-2">-{event.truth_summary.overturned} Inval</span>}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                </div>
            )}
        </div>
    );
};
