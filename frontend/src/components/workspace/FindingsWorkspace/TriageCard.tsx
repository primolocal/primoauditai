"use client";

import React from "react";
import { useAudit } from "../AuditContext";
import { Finding } from "@/types/claim";
import { apiUrl } from "@/lib/api";

const TriageHeader: React.FC<{ nbaFinding: Finding | undefined; onReview: () => void; isManualMode: boolean }> = ({ nbaFinding, onReview, isManualMode }) => {
    return (
        <div className="flex justify-between items-center px-4 py-3 border-b border-slate-200 h-[60px] shrink-0">
            <div className="flex flex-col">
                <span className="text-[10px] font-black uppercase text-slate-500 tracking-widest leading-none mb-1">
                    Next Best Action
                </span>
                <span className="font-bold text-sm text-slate-800 leading-none">
                    {nbaFinding ? nbaFinding.rule_id : (isManualMode ? "MANUAL REVIEW REQUIRED" : "ALL CLEARED")}
                </span>
            </div>
            {nbaFinding && (
                <button 
                    onClick={onReview}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-black uppercase tracking-widest text-[10px] px-4 py-2 rounded shadow-sm transition-colors active:scale-95"
                >
                    Review Immediate
                </button>
            )}
        </div>
    );
};

const ManualReviewModeBanner: React.FC<{ onRetry: () => void; isRetrying: boolean }> = ({ onRetry, isRetrying }) => {
    return (
        <div className="mx-4 mt-2 mb-3 bg-slate-50 border border-slate-200 rounded-[6px] flex flex-col overflow-hidden">
            <div className="border-b border-slate-200 px-4 py-3 flex items-center justify-between bg-white">
                <span className="font-black text-[11px] uppercase tracking-widest text-slate-800 flex items-center gap-2">
                    <span className="text-slate-500">🛠</span> MANUAL REVIEW MODE
                </span>
                <button 
                    onClick={onRetry}
                    disabled={isRetrying}
                    className="bg-slate-800 hover:bg-slate-900 disabled:bg-slate-400 text-white text-[9px] font-black px-3 py-2 rounded uppercase tracking-widest shadow-sm transition-colors active:scale-95 flex items-center gap-2"
                >
                    {isRetrying ? (
                        <>
                            <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Running Hermes Audit...
                        </>
                    ) : "Run Hermes Audit"}
                </button>
            </div>
            <div className="p-4 flex flex-col">
                <p className="text-sm font-bold text-slate-800 mb-1">Automated triage unavailable</p>
                <p className="text-xs text-slate-600 mb-4">You can proceed with manual audit. No blocking rules enforced.</p>
                <div className="bg-[#fffdf5] border border-amber-200/60 rounded px-3 py-2.5 flex items-start gap-2 shadow-sm">
                    <span className="text-amber-600 font-black text-[10px] uppercase mt-0.5 tracking-widest">Tip:</span>
                    <span className="text-xs text-amber-900 font-medium">Focus on missing photos, part usage, and labor justification first</span>
                </div>
            </div>
        </div>
    );
};

const HermesTaskEngine: React.FC<{ tasks: any[]; auditRun: any; onSelect: (id: string) => void; setAuditRun: any }> = ({ tasks, auditRun, onSelect, setAuditRun }) => {
    if (!tasks || tasks.length === 0) return null;

    const firstPendingIdx = tasks.findIndex(t => t.status === 'pending');

    return (
        <div className="mx-4 mt-2 mb-3 px-[14px] py-[10px] bg-rose-50/50 border border-rose-100 border-l-[4px] border-l-rose-500 rounded-[6px]">
            <div className="flex items-center gap-2 mb-1">
                <span className="font-black text-[11px] uppercase tracking-widest text-rose-800">[NEXT ACTION – REQUIRED]</span>
            </div>
            <ul className="flex flex-col gap-3 mt-3">
                {tasks.map((task, idx) => {
                    // Task formatting
                    const finding = auditRun?.findings?.find((f: any) => f.id === task.finding_id);
                    const affectedLines = finding?.affected_lines || [];
                    
                    let lineLabel = `Rule ${finding?.rule_id || task.label || "N/A"}`;
                    if (affectedLines.length > 0 && auditRun?.estimate_lines?.items) {
                        const primLine = auditRun.estimate_lines.items.find((l: any) => affectedLines.includes(l.line_no));
                        if (primLine && primLine.description) {
                            lineLabel = `Line ${primLine.line_no} – ${primLine.description}`;
                        } else if (affectedLines[0] === 0) {
                            lineLabel = `Admin – ${finding?.category || 'General Form'}`;
                        }
                    } else if (finding) {
                        lineLabel = finding.category || lineLabel;
                    }

                    const isResolved = task.status === 'resolved';
                    const isActive = idx === firstPendingIdx;
                    const isLocked = !isResolved && !isActive;

                    if (isResolved) return null;

                    if (isLocked) {
                        return (
                            <li key={task.id} className="flex items-center gap-2 text-xs text-slate-500 opacity-70">
                                <span className="text-sm">🔒</span>
                                <span className="font-medium">{lineLabel}</span>
                            </li>
                        );
                    }

                    const handleTaskAction = async (action: string) => {
                        try {
                            const res = await fetch(apiUrl(`/api/audits/${auditRun.run_id}/findings/${task.finding_id}/${action}`), { method: 'POST' });
                            if (res.ok) {
                                const data = await res.json();
                                const updatedRun = { ...auditRun, scorecard: data.scorecard, narrative: data.narrative, findings: auditRun.findings.map((f: any) => f.id === task.finding_id ? data.finding : f) };
                                setAuditRun(updatedRun);
                            }
                        } catch (e) {}
                    };

                    return (
                        <li key={task.id} className="flex flex-col gap-2">
                            <div className="flex items-center gap-2 text-xs text-rose-900 font-bold">
                                <span>➡</span>
                                <span className="cursor-pointer hover:underline" onClick={() => onSelect(task.finding_id)}>{lineLabel}</span>
                                {task.score_impact > 0 && (
                                    <span className="text-[10px] font-black bg-rose-200 text-rose-800 px-1.5 py-0.5 rounded ml-auto">
                                        +{task.score_impact} SCORE
                                    </span>
                                )}
                            </div>
                            <div className="flex gap-2 mt-1">
                                <button onClick={() => handleTaskAction('confirm')} className="flex-1 bg-white border border-rose-300 hover:bg-rose-50 text-rose-800 text-[9px] font-black py-1.5 rounded uppercase tracking-widest shadow-sm transition-colors active:scale-95">
                                    Request Info
                                </button>
                                <button onClick={() => handleTaskAction('overturn')} className="flex-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-[9px] font-black py-1.5 rounded uppercase tracking-widest shadow-sm transition-colors active:scale-95">
                                    Override
                                </button>
                                <button onClick={() => handleTaskAction('confirm')} className="flex-1 bg-rose-600 hover:bg-rose-700 text-white text-[9px] font-black py-1.5 rounded uppercase tracking-widest shadow-sm transition-colors active:scale-95">
                                    Confirm
                                </button>
                            </div>
                        </li>
                    );
                })}
            </ul>
        </div>
    );
};

const AuditProgress: React.FC<{ totalCount: number; resolvedCount: number }> = ({ totalCount, resolvedCount }) => {
    if (totalCount === 0) return null;
    const pct = Math.round((resolvedCount / totalCount) * 100);

    return (
        <div className="px-4 pb-4 mt-2 flex flex-col gap-2">
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                <div 
                    className="bg-emerald-500 h-full transition-all duration-500 ease-out" 
                    style={{ width: `${pct}%` }} 
                />
            </div>
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 text-right">
                {resolvedCount} of {totalCount} Findings Resolved
            </div>
        </div>
    );
};

export const TriageCard: React.FC = () => {
    const { auditRun, setSelectedFindingId, setAuditRun } = useAudit();
    const [isRetrying, setIsRetrying] = React.useState(false);
    
    if (!auditRun) return null;

    const nbaFinding = (auditRun.findings || []).find((f: Finding) => f.status === 'open');
    const hermesTasks = auditRun.hermes_tasks;
    
    // Deterministic override check
    const manualModeActive = auditRun.manual_review_mode === true;
    
    // Only use tasks if explicit manual mode is false and tasks are populated
    const useTasks = !manualModeActive && hermesTasks && hermesTasks.tasks && hermesTasks.tasks.length > 0;
    
    // We update progress against hermes_tasks total
    const totalCount = useTasks ? hermesTasks.total_tasks : (auditRun.findings || []).length;
    const resolvedCount = useTasks ? hermesTasks.resolved_tasks : (auditRun.findings || []).filter((f: Finding) => f.status !== 'open').length;

    const onReviewImmediate = () => {
        if (nbaFinding) {
            setSelectedFindingId(nbaFinding.id);
            document.getElementById(`finding-${nbaFinding.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    };

    const handleSelectTriageItem = (id: string) => {
        setSelectedFindingId(id);
        document.getElementById(`finding-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };

    const handleRetryHermes = async () => {
        setIsRetrying(true);
        try {
            const res = await fetch(apiUrl(`/api/audits/${auditRun.run_id}/retry-hermes`), { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                setAuditRun(data);
            }
        } catch (e) {
            console.error("Retry failed", e);
        } finally {
            setIsRetrying(false);
        }
    };

    return (
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden flex flex-col mb-4">
            <TriageHeader 
                nbaFinding={nbaFinding} 
                onReview={onReviewImmediate} 
                isManualMode={manualModeActive}
            />
            {manualModeActive && (
                <ManualReviewModeBanner 
                    onRetry={handleRetryHermes} 
                    isRetrying={isRetrying} 
                />
            )}
            {useTasks && (
                <HermesTaskEngine 
                    tasks={hermesTasks.tasks} 
                    auditRun={auditRun}
                    onSelect={handleSelectTriageItem}
                    setAuditRun={setAuditRun}
                />
            )}
            <AuditProgress 
                totalCount={totalCount} 
                resolvedCount={resolvedCount} 
            />
        </div>
    );
};
