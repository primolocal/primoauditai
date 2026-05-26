"use client";

import React, { useState, useCallback } from "react";
import { Finding } from "@/types/claim";
import { useAuditInteraction, useAuditData } from "../AuditContext";
import { getFindingEvidenceHealth, getExpectedSupportTypes } from "@/lib/evidenceAssessment";
import { PhotoConfirmationBlock } from "./PhotoConfirmationBlock";
import { apiUrl } from "@/lib/api";

// ─── Module-level static maps (memoized once at import time) ───
const sevColors: Record<string, string> = {
    critical: "bg-red-500", high: "bg-orange-500",
    major: "bg-orange-500", medium: "bg-amber-500",
    minor: "bg-blue-500", low: "bg-slate-400",
};

const statusMap: Record<string, string> = {
    open: "text-slate-500 border-slate-200 bg-white",
    confirmed: "text-emerald-700 border-emerald-200 bg-emerald-50",
    overturned: "text-purple-700 border-purple-200 bg-purple-50",
    needs_review: "text-amber-700 border-amber-200 bg-amber-50",
    deferred: "text-blue-700 border-blue-200 bg-blue-50"
};

function getEvBadge(health: string): { label: string; icon: string; color: string } {
    if (health === 'Strong Support') return { label: "Strong Support", icon: "✅", color: "text-emerald-700 bg-emerald-50 border-emerald-200" };
    if (health === 'Weak Support') return { label: "Weak Support", icon: "⚠️", color: "text-amber-700 bg-amber-50 border-amber-200 hover:border-amber-400" };
    if (health === 'Invalid Support') return { label: "Invalid Support", icon: "❌", color: "text-red-700 bg-red-50 border-red-200" };
    if (health === 'Missing Required Evidence') return { label: "Missing Evidence", icon: "❗", color: "text-red-800 bg-red-100 border-red-300 font-bold" };
    if (health === 'Reviewer Overrode System') return { label: "System Overridden", icon: "👁️", color: "text-purple-700 bg-purple-50 border-purple-200 font-bold" };
    return { label: health as string, icon: "ℹ️", color: "text-slate-700 bg-slate-50 border-slate-200" };
}

interface Props {
    finding: Finding;
    isSelected: boolean;
    isExpanded: boolean;
    onToggleExpand: (id: string) => void;
    allAssets: any[];
    healthResult: any;
}

const FindingCardInner: React.FC<Props> = ({ finding, isSelected, isExpanded, onToggleExpand, allAssets, healthResult }) => {
    const { setSelectedFindingId, verdictStore, reviewerNotes, setReviewerNotes, saveReviewerNote, photoConfirmations, setActiveInspectorTab } = useAuditInteraction();
    const { auditRun, setAuditRun } = useAuditData();

    const [actionError, setActionError] = useState<string | null>(null);
    const [actionLoading, setActionLoading] = useState<string | null>(null);

    const color = sevColors[finding.severity?.toLowerCase() || "low"] || "bg-slate-400";
    const sColor = statusMap[finding.status] || statusMap.open;

    const health = healthResult ? healthResult.status : 'Pending Review';
    const explanation = healthResult ? healthResult.explanation : 'Finding is awaiting review.';

    const expectations = getExpectedSupportTypes(finding.category);
    const isPhotoRequired = expectations.primary.includes('photo');
    const linkedCount = isPhotoRequired ? (photoConfirmations[finding.id]?.linked_asset_ids?.length || 0) : 0;

    const evBadge = getEvBadge(health);

    const handleSelect = useCallback(() => {
        setSelectedFindingId(finding.id);
        onToggleExpand(finding.id);
    }, [finding.id, setSelectedFindingId, onToggleExpand]);

    const handleAction = useCallback(async (action: 'confirm' | 'overturn') => {
        if (!auditRun) return;
        setActionError(null);
        setActionLoading(action);
        try {
            const res = await fetch(apiUrl(`/audits/${auditRun.run_id}/findings/${finding.id}/${action}`), {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                const updatedRun = {
                    ...auditRun,
                    scorecard: data.scorecard,
                    narrative: data.narrative,
                    findings: auditRun.findings.map((f: Finding) => f.id === finding.id ? data.finding : f)
                };
                setAuditRun(updatedRun);
            } else {
                const errText = await res.text().catch(() => "Unknown error");
                setActionError(`Failed to ${action} finding: ${res.status} ${errText.slice(0, 100)}`);
            }
        } catch (err) {
            console.error(err);
            setActionError(`Network error while trying to ${action} finding. Check your connection.`);
        } finally {
            setActionLoading(null);
        }
    }, [auditRun, finding.id, setAuditRun]);

    return (
        <div 
            className={`relative border rounded overflow-hidden transition-all duration-100 cursor-pointer 
                ${isSelected ? 'bg-blue-50/30 border-blue-300 shadow-md z-10 ring-1 ring-blue-400' : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50'}
                ${finding.status !== 'open' ? 'opacity-70 saturate-50' : ''}
            `}
            onClick={() => {
                if (!isSelected) setSelectedFindingId(finding.id);
            }}
        >
            {/* Severity Left Bar */}
            <div className={`absolute left-0 top-0 w-1.5 h-full ${color}`} />
            
            <div className="p-3 pl-4 flex flex-col gap-2 relative">
                {/* Dense Header Row */}
                <div 
                    className="flex flex-col gap-2 relative w-full"
                    onClick={(e) => {
                        e.stopPropagation();
                        handleSelect();
                    }}
                >
                    {/* Top Row: Rule ID, Subject Label, Impact, Status */}
                    <div className="flex justify-between items-start gap-4">
                        <div className="flex flex-col flex-1 min-w-0 pr-4">
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest">{finding.rule_id}</span>
                                {finding.is_supplement_issue && (
                                    <span className="text-[8px] leading-none bg-purple-50 text-purple-700 font-black uppercase tracking-widest px-1 py-0.5 rounded border border-purple-200">SUPP</span>
                                )}
                            </div>
                            
                            {/* DETERMINISTIC SUBJECT LABEL */}
                            <h3 className="text-sm font-black text-slate-900 leading-tight truncate w-full">
                                {(() => {
                                    let label = finding.rule_id;
                                    if (finding.category) label = finding.category;
                                    
                                    if (auditRun && finding.affected_lines && finding.affected_lines.length > 0) {
                                        const lineItem = auditRun.estimate_lines?.items?.find((l: any) => finding.affected_lines.includes(l.line_no));
                                        if (lineItem) {
                                            if (lineItem.description && lineItem.description.trim() !== "") label = lineItem.description;
                                            else if (lineItem.part_type && lineItem.part_type.trim() !== "") label = lineItem.part_type;
                                            else if (lineItem.operation && lineItem.operation.trim() !== "") label = lineItem.operation;
                                        }
                                    }
                                    return label;
                                })()}
                            </h3>
                        </div>
                        
                        <div className="flex gap-4 items-center shrink-0">
                            {/* Impact */}
                            <div className="flex flex-col pr-4 border-r border-slate-200 items-end">
                                <span className="text-[9px] uppercase font-black text-slate-500 tracking-wider">Impact</span>
                                <span className={`text-xs font-mono font-bold ${finding.financial_impact && finding.financial_impact > 0 ? 'text-red-600' : 'text-slate-500'}`}>
                                    ${finding.financial_impact?.toFixed(2) || '0.00'}
                                </span>
                            </div>
                            
                            {/* Status */}
                            <span className={`text-[10px] uppercase font-black tracking-widest px-2 py-1 rounded border min-w-[90px] w-[90px] flex justify-center items-center transition-colors ${sColor}`}>
                                {finding.status}
                            </span>
                        </div>
                    </div>

                    {/* Bottom Row: Evidence Hooks & Messages */}
                    <div className="flex items-center gap-2 mt-1">
                        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded border text-[9px] font-bold uppercase tracking-wider shrink-0 ${evBadge.color}`}>
                            <span>{evBadge.icon}</span> {evBadge.label}
                        </div>
                        
                        {isPhotoRequired && (
                            <div 
                                className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-600 text-[9px] font-bold uppercase tracking-wider shrink-0 cursor-pointer hover:bg-slate-200 hover:text-slate-800 transition-colors"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedFindingId(finding.id);
                                    setActiveInspectorTab('evidence');
                                }}
                                title="Jump to Evidence Workspace"
                            >
                                <span>📷</span>
                                {linkedCount} Linked
                            </div>
                        )}

                        {/* Short Reason Hook */}
                        <div className="flex items-center w-full min-w-0 ml-2">
                             <span className="text-xs text-slate-600 font-medium truncate w-full">{finding.message}</span>
                        </div>
                    </div>
                </div>
                
                {/* Expanded State Content */}
                {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-slate-200">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Detailed Left */}
                            <div className="space-y-4">
                                <div>
                                    <h4 className="text-[10px] uppercase font-black text-slate-500 tracking-widest mb-1.5">Full Message</h4>
                                    <p className="text-xs text-slate-700 italic border-l-2 border-slate-300 pl-2 leading-relaxed">
                                        "{finding.message}"
                                    </p>
                                </div>
                                
                                {finding.hermes_critique && (
                                    <div className="bg-purple-50 border-l-4 border-purple-500 p-3 rounded-r relative shadow-sm mb-4">
                                        <div className="absolute top-0 right-0 py-1 px-2 bg-purple-100 text-[8px] font-black uppercase tracking-widest text-purple-600 rounded-bl border-b border-l border-purple-200">PrimoAudit Intelligence</div>
                                        <h4 className="text-[10px] uppercase font-black text-purple-700 tracking-widest mb-1 flex items-center gap-1">
                                            <span>⚡</span> Critique Note
                                        </h4>
                                        <p className="text-xs text-purple-900 leading-relaxed font-medium">
                                            {finding.hermes_critique}
                                        </p>
                                        {finding.guideline_citation && (
                                            <div className="mt-2 text-[9px] text-purple-500 font-bold uppercase tracking-widest">
                                                Citation: {finding.guideline_citation}
                                            </div>
                                        )}
                                    </div>
                                )}
                                
                                {finding.suggested_action_type && (
                                    <div className="bg-slate-50 border-l-4 border-blue-400 p-3 rounded-r relative shadow-sm mb-4">
                                        <div className="absolute top-0 right-0 py-1 px-2 bg-blue-100 text-[8px] font-black uppercase tracking-widest text-blue-600 rounded-bl border-b border-l border-blue-200">Advisory Only</div>
                                        <h4 className="text-[10px] uppercase font-black text-blue-700 tracking-widest mb-1.5 flex items-center gap-1">
                                            <span>💡</span> PrimoAudit Intelligence Recommendation
                                        </h4>
                                        <div className="space-y-2 mt-2">
                                            <div className="flex items-center gap-2">
                                                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Type:</span>
                                                <span className="text-xs font-mono bg-white border border-slate-200 px-1.5 py-0.5 rounded text-blue-800">{finding.suggested_action_type}</span>
                                            </div>
                                            
                                            {finding.suggested_revision && (
                                                <div className="text-xs bg-white border border-slate-200 p-2 rounded">
                                                    <div className="flex items-center justify-between mb-1 pb-1 border-b border-slate-100">
                                                        <span className="text-[10px] font-bold text-slate-500 uppercase">Suggested Revision ({finding.suggested_revision.field})</span>
                                                    </div>
                                                    <div className="flex items-center gap-2 mt-1 font-mono text-sm">
                                                        <span className="text-red-500 line-through decoration-red-300">{finding.suggested_revision.current_value}</span>
                                                        <span className="text-slate-400">→</span>
                                                        <span className="text-emerald-600 bg-emerald-50 px-1 border border-emerald-200 rounded">{finding.suggested_revision.suggested_value}</span>
                                                    </div>
                                                    {finding.suggested_revision.reason && (
                                                        <div className="mt-2 text-[10px] text-slate-600 italic">"{finding.suggested_revision.reason}"</div>
                                                    )}
                                                </div>
                                            )}
                                            
                                            {finding.supporting_reason && (
                                                <div className="text-[10px] text-slate-600 border-l-2 border-blue-100 pl-2 mt-2">
                                                    <span className="font-bold text-slate-500 mr-1 pb-1 flex border-b border-blue-100 uppercase tracking-widest">Rationale</span>
                                                    <span className="mt-1 block">{finding.supporting_reason}</span>
                                                </div>
                                            )}
                                            
                                            {finding.requires_manual_confirmation && (
                                                <div className="flex items-center justify-end mt-2 pt-1">
                                                    <span className="flex items-center gap-1 px-1.5 py-0.5 bg-amber-50 border border-amber-200 text-amber-700 text-[8px] font-black uppercase tracking-widest rounded">
                                                        <span>⚠️</span> Manual Confirmation Required
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                <div>
                                    <h4 className="text-[10px] uppercase font-black text-slate-500 tracking-widest mb-1.5">Action Recommended</h4>
                                    <div className="bg-slate-50 border border-slate-200 p-2 rounded text-xs space-y-1">
                                        <div className="text-slate-800">{finding.recommended_action}</div>
                                    </div>
                                </div>
                            </div>
                            
                            {/* Detailed Right - Actions */}
                            <div className="space-y-4">
                                <PhotoConfirmationBlock finding={finding} />

                                <div className="space-y-2">
                                    <h4 className="text-[10px] uppercase font-black text-blue-600 tracking-widest mb-1.5 border-b border-blue-200 pb-1">Reviewer Actions</h4>
                                    <button
                                        disabled={!!actionLoading}
                                        className={`w-full flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-widest px-3 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 hover:text-emerald-800 active:scale-[0.98] border border-emerald-200 hover:border-emerald-300 rounded shadow-sm transition-all ${
                                            actionLoading ? "opacity-50 cursor-not-allowed" : ""
                                        }`}
                                        onClick={(e) => { e.stopPropagation(); handleAction('confirm'); }}
                                    >
                                        {actionLoading === 'confirm' ? (
                                            <span className="inline-block w-3 h-3 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></span>
                                        ) : null}
                                        Confirm
                                    </button>
                                    <button
                                        disabled={!!actionLoading}
                                        className={`w-full flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-widest px-3 py-2 bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 active:scale-[0.98] border border-slate-300 hover:border-slate-400 rounded shadow-sm transition-all ${
                                            actionLoading ? "opacity-50 cursor-not-allowed" : ""
                                        }`}
                                        onClick={(e) => { e.stopPropagation(); handleAction('overturn'); }}
                                    >
                                        {actionLoading === 'overturn' ? (
                                            <span className="inline-block w-3 h-3 border-2 border-slate-500 border-t-transparent rounded-full animate-spin"></span>
                                        ) : null}
                                        Dismiss (Overturn)
                                    </button>
                                    {actionError && (
                                        <div className="text-[10px] text-red-700 bg-red-50 border border-red-200 rounded p-2 mt-1 font-bold">
                                            {actionError}
                                        </div>
                                    )}
                                </div>

                                <div className="pt-2">
                                    <h4 className="text-[9px] uppercase font-black text-slate-500 tracking-widest mb-1.5 flex justify-between">
                                        <span>Reviewer Note</span>
                                        {reviewerNotes[finding.id] && <span className="text-emerald-600">Saved</span>}
                                    </h4>
                                    <textarea 
                                        className="w-full text-xs p-2 border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-h-[60px] resize-y placeholder:text-slate-400 text-slate-700"
                                        placeholder="Explain override or detail missing context..."
                                        value={reviewerNotes[finding.id] || ''}
                                        onChange={(e) => setReviewerNotes({...reviewerNotes, [finding.id]: e.target.value})}
                                        onBlur={(e) => saveReviewerNote(finding.id, e.target.value)}
                                        onClick={(e) => e.stopPropagation()}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

// ─── Custom comparison for React.memo: only re-render if finding data, selection, or expansion changes ───
const areEqual = (prev: Props, next: Props): boolean => {
    if (prev.finding !== next.finding) return false;
    if (prev.isSelected !== next.isSelected) return false;
    if (prev.isExpanded !== next.isExpanded) return false;
    // If healthResult changed (verdict/notes/photoConfirmations changed for this finding)
    if (prev.healthResult?.status !== next.healthResult?.status) return false;
    if (prev.allAssets !== next.allAssets) return false;
    return true;
};

export const FindingCard = React.memo(FindingCardInner, areEqual);
