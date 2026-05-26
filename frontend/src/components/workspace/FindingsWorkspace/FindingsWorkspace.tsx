"use client";

import React, { useEffect, useMemo, useState, useCallback } from "react";
import { useAuditData, useAuditInteraction, useSync } from "../AuditContext";
import { FindingToolbar } from "./FindingToolbar";
import { FindingCard } from "./FindingCard";
import { Finding } from "@/types/claim";
import { getFindingEvidenceHealth, getClaimReadiness, getExpectedSupportTypes, FindingEvidenceHealth, FindingHealthScore } from "@/lib/evidenceAssessment";
import { apiUrl } from "@/lib/api";

export const FindingsWorkspace: React.FC = () => {
    const { auditRun, setAuditRun, selectedFinding: selectedFindingFromData } = useAuditData();
    const { selectedFindingId, setSelectedFindingId, setActiveInspectorTab, verdictStore, reviewerNotes, photoConfirmations } = useAuditInteraction();
    const { syncState, lastSavedAt, unsyncedCount, retrySync } = useSync();
    const [healthFilter, setHealthFilter] = useState<FindingEvidenceHealth | null>(null);
    const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [sortBy, setSortBy] = useState("severity");
    const [statusFilter, setStatusFilter] = useState<string | null>(null);
    const [severityFilter, setSeverityFilter] = useState<string | null>(null);

    if (!auditRun) return null;

    // ── Memoize sorted findings ──
    const sortedFindings = useMemo(() => {
        return [...auditRun.findings].sort((a, b) => {
            // first pass: open status always first
            if (a.status === 'open' && b.status !== 'open') return -1;
            if (a.status !== 'open' && b.status === 'open') return 1;

            switch (sortBy) {
                case "line_number": {
                    const aLine = a.affected_lines?.[0] ?? 9999;
                    const bLine = b.affected_lines?.[0] ?? 9999;
                    return aLine - bLine;
                }
                case "confidence": {
                    const aConf = a.confidence || 0;
                    const bConf = b.confidence || 0;
                    return bConf - aConf;
                }
                case "financial_impact": {
                    const aImpact = a.financial_impact || 0;
                    const bImpact = b.financial_impact || 0;
                    return bImpact - aImpact;
                }
                case "severity":
                default: {
                    const sevOrder: Record<string, number> = { critical: 0, high: 1, major: 2, medium: 3, minor: 4, low: 5 };
                    const aSev = sevOrder[a.severity?.toLowerCase() || "low"] ?? 99;
                    const bSev = sevOrder[b.severity?.toLowerCase() || "low"] ?? 99;
                    if (aSev !== bSev) return aSev - bSev;

                    const aImpact = a.financial_impact || 0;
                    const bImpact = b.financial_impact || 0;
                    if (aImpact !== bImpact) return bImpact - aImpact;

                    const aConf = a.confidence || 0;
                    const bConf = b.confidence || 0;
                    return bConf - aConf;
                }
            }
        });
    }, [auditRun.findings, sortBy]);

    // ── Memoize allAssets (shared between workspace and FindingCards) ──
    const allAssets = useMemo(() => {
        return auditRun ? [...(auditRun.evidence_matrix.photos || []), ...(auditRun.evidence_matrix.documents || [])] : [];
    }, [auditRun]);

    // ── Memoize finding healths ──
    const findingHealths = useMemo(() => {
        const hm: Record<string, FindingHealthScore> = {};
        auditRun.findings.forEach(f => {
            hm[f.id] = getFindingEvidenceHealth(f, allAssets, verdictStore, reviewerNotes, photoConfirmations);
        });
        return hm;
    }, [auditRun.findings, allAssets, verdictStore, reviewerNotes, photoConfirmations]);

    // ── Memoize claim readiness ──
    const claimReadiness = useMemo(() => {
        return getClaimReadiness(Object.values(findingHealths));
    }, [findingHealths]);

    // ── Memoize filtered findings ──
    const filteredFindings = useMemo(() => {
        return sortedFindings.filter(f => {
            if (healthFilter && findingHealths[f.id].status !== healthFilter) return false;
            if (statusFilter && f.status !== statusFilter) return false;
            if (severityFilter && f.severity?.toLowerCase() !== severityFilter.toLowerCase()) return false;
            if (searchQuery.trim()) {
                const q = searchQuery.toLowerCase();
                const haystack = [
                    f.rule_id,
                    f.message,
                    f.category,
                    f.recommended_action,
                    f.hermes_critique,
                    ...(f.affected_lines?.map(String) || []),
                ].filter(Boolean).join(" ").toLowerCase();
                if (!haystack.includes(q)) return false;
            }
            return true;
        });
    }, [sortedFindings, findingHealths, healthFilter, statusFilter, severityFilter, searchQuery]);

    // ── Single-pass hc counters (was 5 separate iterations) ──
    const hc = useMemo(() => {
        const counts = { strong: 0, weak: 0, invalid: 0, missing: 0, overrides: 0 };
        for (const h of Object.values(findingHealths)) {
            switch (h.status) {
                case 'Strong Support': counts.strong++; break;
                case 'Weak Support': counts.weak++; break;
                case 'Invalid Support': counts.invalid++; break;
                case 'Missing Required Evidence': counts.missing++; break;
                case 'Reviewer Overrode System': counts.overrides++; break;
            }
        }
        return counts;
    }, [findingHealths]);

    // ── Toggle expand callback (stable reference via useCallback) ──
    const handleToggleExpand = useCallback((id: string) => {
        setExpandedFindingId(prev => prev === id ? null : id);
    }, []);

    const triggerAction = useCallback(async (id: string, action: 'confirm' | 'overturn') => {
        try {
            const res = await fetch(apiUrl(`/audits/${auditRun.run_id}/findings/${id}/${action}`), {
                method: 'POST'
            });
            if (res.ok) {
                const data = await res.json();
                const updatedRun = {
                    ...auditRun,
                    scorecard: data.scorecard,
                    narrative: data.narrative,
                    findings: auditRun.findings.map((f: Finding) => f.id === id ? data.finding : f)
                };
                setAuditRun(updatedRun);
            }
        } catch (err) { }
    }, [auditRun, setAuditRun]);

    useEffect(() => {
        const handleKeyDown = async (e: KeyboardEvent) => {
            if (document.activeElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
                return;
            }

            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                if (!selectedFindingId) {
                    setSelectedFindingId(sortedFindings[0]?.id || null);
                    return;
                }
                const currentIndex = sortedFindings.findIndex(f => f.id === selectedFindingId);
                if (currentIndex === -1) return;
                
                const nextIndex = e.key === 'ArrowDown' ? currentIndex + 1 : currentIndex - 1;
                if (nextIndex >= 0 && nextIndex < sortedFindings.length) {
                    setSelectedFindingId(sortedFindings[nextIndex].id);
                    document.getElementById(`finding-${sortedFindings[nextIndex].id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }

            if (selectedFindingId) {
                if (e.key === 'C') { e.preventDefault(); await triggerAction(selectedFindingId, 'confirm'); }
                if (e.key === 'O') { e.preventDefault(); await triggerAction(selectedFindingId, 'overturn'); }
            }
            
            if (e.key === '1') setActiveInspectorTab('estimate');
            if (e.key === '2') setActiveInspectorTab('evidence');
            if (e.key === '3') setActiveInspectorTab('score');
            if (e.key === '4') setActiveInspectorTab('narrative');
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [selectedFindingId, sortedFindings, setActiveInspectorTab, setSelectedFindingId, triggerAction]);

    const nbaFinding = sortedFindings.find(f => f.status === 'open');

    const photoStats = useMemo(() => {
        let stats = { unuploaded: 0, noLinked: 0, noPhotos: 0, unknown: 0, requiredCount: 0 };
        auditRun.findings.forEach(f => {
            const expectations = getExpectedSupportTypes(f.category);
            if (!expectations.primary.includes('photo')) return;
            stats.requiredCount++;
            
            const state = photoConfirmations[f.id];
            if (!state || state.evidence_exists === 'unknown' || !state.evidence_exists) {
                stats.unknown++;
            } else if (state.evidence_exists === 'no') {
                stats.noPhotos++;
            } else if (state.evidence_exists === 'yes' && state.evidence_uploaded === 'no') {
                stats.unuploaded++;
            } else if (state.evidence_exists === 'yes' && state.evidence_uploaded === 'yes') {
                if (!state.linked_asset_ids || state.linked_asset_ids.length === 0) {
                    stats.noLinked++;
                }
            }
        });
        return stats;
    }, [auditRun.findings, photoConfirmations]);

    return (
        <div className="flex flex-col w-full h-full p-4 pb-20 overflow-y-auto">
            {/* Header Area */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                    <div className="text-lg font-black text-slate-900 uppercase tracking-widest flex items-center gap-3">
                        Review Queue
                        <span className="text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full">
                            {sortedFindings.filter(f => f.status === 'open').length} PENDING
                        </span>
                    </div>
                    {/* Top Level Readiness Marker */}
                    <div className={`text-[11px] font-black uppercase tracking-widest px-3 py-1 rounded shadow-sm border ${
                        claimReadiness === 'Ready' 
                            ? 'bg-emerald-600 text-white border-emerald-800' 
                            : claimReadiness === 'Risky'
                                ? 'bg-amber-500 text-white border-amber-700'
                                : 'bg-red-600 text-white border-red-800 animate-pulse'
                    }`}>
                        {claimReadiness}
                    </div>
                </div>
                
                {/* Saving Indicator */}
                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest h-6">
                    {syncState === 'saving' && (
                        <div className="flex items-center gap-1.5 text-emerald-600 transition-opacity animate-pulse">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                            <span>Syncing...</span>
                        </div>
                    )}
                    {syncState === 'saved' && lastSavedAt && (
                        <div className="flex items-center gap-1.5 text-slate-400">
                            <span className="text-emerald-500 text-xs">✓</span>
                            <span>Saved {lastSavedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                    )}
                    {syncState === 'error' && (
                        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-600 px-2 py-0.5 rounded shadow-sm">
                            <span className="text-red-500">⚠ {unsyncedCount} unsynced changes</span>
                            <button onClick={retrySync} className="hover:text-red-800 underline ml-1 cursor-pointer transition-colors">[Retry]</button>
                        </div>
                    )}
                </div>
            </div>

            {/* Claim Readiness Summary */}
            <div className="grid grid-cols-5 gap-2 mb-4">
                <div className="bg-emerald-50 border border-emerald-200 p-2 rounded flex flex-col items-center justify-center shadow-sm">
                    <span className="text-emerald-700 font-black text-sm">{hc.strong}</span>
                    <span className="text-[8px] uppercase font-black tracking-widest text-emerald-600 text-center mt-0.5">Strong</span>
                </div>
                <div className="bg-amber-50 border border-amber-200 p-2 rounded flex flex-col items-center justify-center shadow-sm">
                    <span className="text-amber-700 font-black text-sm">{hc.weak}</span>
                    <span className="text-[8px] uppercase font-black tracking-widest text-amber-600 text-center mt-0.5">Weak</span>
                </div>
                <div className="bg-red-50 border border-red-200 p-2 rounded flex flex-col items-center justify-center shadow-sm">
                    <span className="text-red-700 font-black text-sm">{hc.invalid}</span>
                    <span className="text-[8px] uppercase font-black tracking-widest text-red-600 text-center mt-0.5">Invalid</span>
                </div>
                <div className="bg-red-100 border border-red-300 p-2 rounded flex flex-col items-center justify-center shadow-sm">
                    <span className="text-red-800 font-black text-sm">{hc.missing}</span>
                    <span className="text-[8px] uppercase font-black tracking-widest text-red-700 text-center mt-0.5">Missing</span>
                </div>
                <div className="bg-purple-50 border border-purple-200 p-2 rounded flex flex-col items-center justify-center shadow-sm">
                    <span className="text-purple-700 font-black text-sm">{hc.overrides}</span>
                    <span className="text-[8px] uppercase font-black tracking-widest text-purple-600 text-center mt-0.5">Overrides</span>
                </div>
            </div>

            {/* Photo Compliance Summary Banner */}
            {photoStats.requiredCount > 0 && (
                <div className="bg-white border text-center shadow-sm border-slate-200 rounded p-3 mb-4 flex gap-4 text-[10px] uppercase font-black tracking-widest text-slate-600 flex-wrap">
                    <div className="text-slate-800 border-r border-slate-300 pr-4 flex items-center gap-1.5 "><span>📷</span> Photo Verification <span className="bg-slate-100 border border-slate-200 px-1.5 rounded">{photoStats.requiredCount} REQ</span></div>
                    {photoStats.unknown > 0 && <span className="flex items-center gap-1 text-amber-600"><span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> {photoStats.unknown} Unknown</span>}
                    {photoStats.noLinked > 0 && <span className="flex items-center gap-1 text-blue-600"><span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span> {photoStats.noLinked} Missing Links</span>}
                    {photoStats.unuploaded > 0 && <span className="flex items-center gap-1 text-purple-600"><span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span> {photoStats.unuploaded} Not Uploaded</span>}
                    {photoStats.noPhotos > 0 && <span className="flex items-center gap-1 text-slate-400"><span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> {photoStats.noPhotos} No Photos</span>}
                    {photoStats.unknown === 0 && photoStats.noLinked === 0 && photoStats.unuploaded === 0 && photoStats.noPhotos === 0 && (
                        <span className="flex items-center gap-1 text-emerald-600">
                             <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> All Photos Verified
                        </span>
                    )}
                </div>
            )}

            {/* Health Filter Bar */}
            <div className="flex flex-wrap items-center gap-2 mb-5 pb-4 border-b border-slate-200">
                <span className="text-[9px] uppercase font-black text-slate-500 tracking-widest mr-2">Health Filter:</span>
                <button onClick={() => setHealthFilter(null)} className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${!healthFilter ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50'}`}>All</button>
                <button onClick={() => setHealthFilter('Strong Support')} className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${healthFilter === 'Strong Support' ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50'}`}>Strong</button>
                <button onClick={() => setHealthFilter('Weak Support')} className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${healthFilter === 'Weak Support' ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50'}`}>Weak</button>
                <button onClick={() => setHealthFilter('Missing Required Evidence')} className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${healthFilter === 'Missing Required Evidence' ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50'}`}>Missing</button>
                <button onClick={() => setHealthFilter('Reviewer Overrode System')} className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${healthFilter === 'Reviewer Overrode System' ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50'}`}>Overrides</button>
            </div>

            {/* Blocker Strip */}
            {auditRun.blockers && auditRun.blockers.length > 0 && (
                <div className="relative bg-red-50 border border-red-200 rounded mb-5 shadow-sm overflow-hidden">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-600"></div>
                    <div className="p-3 pl-4 flex flex-col justify-center">
                        <div className="text-[9px] font-black tracking-widest text-red-700 uppercase flex items-center gap-2">
                            <span className="text-xs">⚠️</span> CRITICAL READINESS BLOCKERS
                        </div>
                        <div className="mt-1 flex flex-col gap-0.5">
                            {auditRun.blockers.map((b, i) => (
                                <div key={i} className="text-[11px] text-red-700 font-mono tracking-tight">- {b}</div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* NBA Banner */}
            {nbaFinding && (
                <div className="relative bg-gradient-to-r from-blue-50 to-white border border-blue-200 rounded p-4 mb-6 flex justify-between items-center shadow-sm overflow-hidden">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600"></div>
                    <div className="flex flex-col pl-2">
                        <span className="text-[9px] font-black uppercase text-blue-700 tracking-widest mb-1">Next Best Action</span>
                        <div className="text-sm text-slate-900 font-bold">{nbaFinding.rule_id}</div>
                        <div className="text-xs text-slate-600 italic">"{nbaFinding.recommended_action}"</div>
                    </div>
                    <button 
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-[10px] font-black uppercase tracking-widest rounded shadow-sm transition-all"
                        onClick={() => setSelectedFindingId(nbaFinding.id)}
                    >
                        Review Immediate
                    </button>
                </div>
            )}
            
            {/* Helper Shortcut Legend */}
            <div className="text-[8px] font-black uppercase tracking-widest text-slate-500 mb-2 flex items-center gap-4 border-b border-slate-200 pb-2 mt-2">
                <span>Keyboard Nav: [1-4] Tabs</span>
                <span>[↑/↓] Select</span>
                <span>[Shift+C] Confirm</span>
                <span>[Shift+O] Overturn</span>
            </div>

            <FindingToolbar
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                sortBy={sortBy}
                onSortChange={setSortBy}
                statusFilter={statusFilter}
                onStatusFilterChange={setStatusFilter}
                severityFilter={severityFilter}
                onSeverityFilterChange={setSeverityFilter}
                totalCount={sortedFindings.length}
                openCount={sortedFindings.filter(f => f.status === 'open').length}
            />

            <div className="flex flex-col space-y-2 pt-4">
                {filteredFindings.map(f => (
                    <div key={f.id} id={`finding-${f.id}`}>
                        <FindingCard
                            finding={f}
                            isSelected={selectedFindingId === f.id}
                            isExpanded={expandedFindingId === f.id}
                            onToggleExpand={handleToggleExpand}
                            allAssets={allAssets}
                            healthResult={findingHealths[f.id] || null}
                        />
                    </div>
                ))}
            </div>

            {/* Bottom spacer for scroll clearance over tray */}
            <div className="h-24 shrink-0"></div>
        </div>
    );
};
