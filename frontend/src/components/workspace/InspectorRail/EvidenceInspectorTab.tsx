"use client";
import React, { useState } from "react";
import { useAudit } from "../AuditContext";
import { NormalizedDocument, PhotoEvidence, EvidenceRef } from "@/types/claim";
import { AssetDetailPanel } from './AssetDetailPanel';
import { getExpectedSupportTypes } from '@/lib/evidenceAssessment';
import { StatusBadge } from '@/app/components/shared/StatusBadge';

export { StatusBadge };

export const EvidenceInspectorTab: React.FC = () => {
    const { auditRun, selectedFinding, photoConfirmations, savePhotoConfirmation } = useAudit();
    
    const toggleLink = (assetId: string) => {
        if (!selectedFinding) return;
        const currentList = photoConfirmations[selectedFinding.id]?.linked_asset_ids || [];
        let newList = [...currentList];
        if (newList.includes(assetId)) {
            newList = newList.filter(id => id !== assetId);
        } else {
            newList.push(assetId);
        }
        savePhotoConfirmation(selectedFinding.id, { linked_asset_ids: newList });
    };
    
    // UI State
    const [filterBy, setFilterBy] = useState<'all' | 'photos' | 'docs' | 'cv_tagged' | 'fixtures' | 'failed'>('all');
    const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'confidence' | 'linked_first'>('newest');
    const [inspectedAssetId, setInspectedAssetId] = useState<string | null>(null);

    // Safe Check
    if (!auditRun) return null;
    const matrix = auditRun.evidence_matrix;
    const docs = matrix.documents || [];
    const photos = matrix.photos || [];

    // Linked Context
    const refs = selectedFinding?.evidence_refs || [];
    const hasGap = refs.filter(r => r.support_status === 'missing').length > 0;
    
    // Heuristics: Potential Support & Mismatches
    const category = selectedFinding?.category || '';
    const expectations = getExpectedSupportTypes(category);
    const potentialSupportCount = [...docs, ...photos].filter(a => {
        if (a.is_mock || !a.confidence || a.confidence < 0.5) return false;
        const typeMatch = ('type' in a && expectations.primary.includes('photo')) || (!('type' in a) && expectations.primary.includes('document'));
        return typeMatch;
    }).length;
        
    // Filtering Logic
    const applyFilter = (asset: NormalizedDocument | PhotoEvidence, isPhoto: boolean) => {
        if (filterBy === 'photos' && !isPhoto) return false;
        if (filterBy === 'docs' && isPhoto) return false;
        if (filterBy === 'cv_tagged' && (!asset.confidence || asset.confidence <= 0)) return false;
        if (filterBy === 'fixtures' && (!asset.is_mock && asset.source_kind !== 'generated_fixture')) return false;
        if (filterBy === 'failed' && asset.processing_status === 'complete') return false;
        return true;
    };

    // Sorting Logic
    const applySort = (a: NormalizedDocument | PhotoEvidence, b: NormalizedDocument | PhotoEvidence) => {
        if (sortBy === 'confidence') return (b.confidence || 0) - (a.confidence || 0);
        if (sortBy === 'linked_first') {
            const explicitLinked = photoConfirmations[selectedFinding?.id || ""]?.linked_asset_ids || [];
            const aLinked = refs.some(r => r.source_id === a.id) || explicitLinked.includes(a.id);
            const bLinked = refs.some(r => r.source_id === b.id) || explicitLinked.includes(b.id);
            if (aLinked && !bLinked) return -1;
            if (!aLinked && bLinked) return 1;
        }
        const timeA = new Date(a.ingested_at || 0).getTime();
        const timeB = new Date(b.ingested_at || 0).getTime();
        return sortBy === 'oldest' ? timeA - timeB : timeB - timeA;
    };

    // Derived Arrays
    const filteredPhotos = photos.filter(p => applyFilter(p, true)).sort(applySort);
    const filteredDocs = docs.filter(d => applyFilter(d, false)).sort(applySort);
    
    // Combine for Navigation
    const unifiedSequence = [...filteredPhotos, ...filteredDocs];

    // Summary Math
    const cvTaggedCount = [...docs, ...photos].filter(x => x.confidence !== undefined && x.confidence > 0).length;
    const fixtureCount = [...docs, ...photos].filter(x => x.source_kind === 'generated_fixture' || x.is_mock).length;

    // ----- DETAIL PANEL TAKEOVER -----
    if (inspectedAssetId) {
        const asset = unifiedSequence.find(a => a.id === inspectedAssetId);
        if (asset) {
            return (
                <AssetDetailPanel 
                    asset={asset}
                    sequence={unifiedSequence}
                    selectedFinding={selectedFinding}
                    refs={refs}
                    setInspectedAssetId={setInspectedAssetId}
                />
            );
        }
        setInspectedAssetId(null);
        return null;
    }

    // ----- STANDARD EVIDENCE LIST VIEW -----
    return (
        <div className="space-y-6">
            
            {/* EVIDENCE MATRIX SUMMARY */}
            <div className="bg-slate-50 border border-slate-200 rounded p-3 shadow-sm">
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-700 mb-2 border-b border-slate-200 pb-1">Asset Pipeline Overview</div>
                <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="bg-white border border-slate-200 rounded p-2 flex flex-col justify-center">
                        <div className="text-xl font-black text-slate-800 leading-tight">{photos.length}</div>
                        <div className="text-[7px] font-black uppercase tracking-widest text-slate-500 mt-1">Photos</div>
                    </div>
                    <div className="bg-white border border-slate-200 rounded p-2 flex flex-col justify-center">
                        <div className="text-xl font-black text-slate-800 leading-tight">{docs.length}</div>
                        <div className="text-[7px] font-black uppercase tracking-widest text-slate-500 mt-1">Docs</div>
                    </div>
                    <div className="bg-blue-50 border border-blue-200 rounded p-2 flex flex-col justify-center">
                        <div className="text-xl font-black text-blue-700 leading-tight">{cvTaggedCount}</div>
                        <div className="text-[7px] font-black uppercase tracking-widest text-blue-600 mt-1">CV Tagged</div>
                    </div>
                    <div className={`border rounded p-2 flex flex-col justify-center ${fixtureCount > 0 ? 'bg-amber-50 border-amber-200' : 'bg-white border-slate-200'}`}>
                        <div className={`text-xl font-black leading-tight ${fixtureCount > 0 ? 'text-amber-700' : 'text-slate-800'}`}>{fixtureCount}</div>
                        <div className={`text-[7px] font-black uppercase tracking-widest mt-1 ${fixtureCount > 0 ? 'text-amber-600' : 'text-slate-500'}`}>Fixtures</div>
                    </div>
                </div>
            </div>

            {/* STATUS / CONTROLS STRIP */}
            <div className="flex flex-col gap-3">
                <div className="flex gap-2 items-center flex-wrap">
                    <span className="text-[9px] uppercase font-black tracking-widest text-slate-500">Filter:</span>
                    {(['all', 'photos', 'docs', 'cv_tagged', 'fixtures', 'failed'] as const).map(f => (
                        <button 
                             key={f} onClick={() => setFilterBy(f)}
                             className={`text-[9px] font-black uppercase tracking-widest px-2 py-1.5 rounded shadow-sm border transition-colors ${
                                filterBy === f ? 'bg-slate-700 text-white border-slate-700' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                             }`}
                        >
                            {f.replace('_', ' ')}
                        </button>
                    ))}
                </div>
                <div className="flex gap-2 items-center">
                    <span className="text-[9px] uppercase font-black tracking-widest text-slate-500">Sort By:</span>
                    <select 
                        className="bg-white border text-[10px] border-slate-300 text-slate-700 shadow-sm rounded px-2 py-1 outline-none font-bold uppercase tracking-wider"
                        value={sortBy} onChange={(e: any) => setSortBy(e.target.value)}
                    >
                        <option value="newest">Newest First</option>
                        <option value="oldest">Oldest First</option>
                        <option value="confidence">Highest CV Confidence</option>
                        <option value="linked_first">Linked Context First</option>
                    </select>
                </div>
            </div>

            {/* LINKED EVIDENCE (Only if finding is selected) */}
            {selectedFinding && (
                <div className="bg-blue-50/30 border border-blue-200 rounded p-3 shadow-sm">
                    <div className="flex justify-between items-center mb-2 pb-1 border-b border-blue-200">
                        <div className="text-[10px] font-black uppercase tracking-widest text-blue-800 truncate pr-2">
                            Linked Evidence: {selectedFinding.rule_id}
                        </div>
                        {hasGap && (
                            <span className="text-[9px] bg-red-50 text-red-600 border border-red-200 px-1.5 py-0.5 rounded font-black uppercase shadow-sm flex-shrink-0">
                                Support Gap
                            </span>
                        )}
                    </div>
                    <div className="flex flex-col gap-2">
                         {refs.length === 0 ? (
                            <div className="bg-white border border-blue-100 rounded p-3 flex flex-col gap-2 shadow-sm">
                                <span className="text-xs text-blue-800 font-bold italic">No deterministic links mapped to this finding by heuristics engine.</span>
                                {potentialSupportCount > 0 && (
                                    <div className="bg-indigo-50 border border-indigo-200 px-2 py-1.5 rounded text-[10px] font-black tracking-widest text-indigo-700 flex items-start gap-2 flex-col">
                                        <span className="uppercase font-bold text-[9px] border-b border-indigo-100 pb-0.5 w-full">💡 Potential Support Elsewhere</span>
                                        <span>{potentialSupportCount} unlinked global assets found matching this rule logic ({expectations.primary.map(t => t === 'photo' ? 'Photos' : 'Documents').join(' / ')}).</span>
                                    </div>
                                )}
                            </div>
                         ) : (
                             refs.map((ref, i) => {
                                 const expectedTypeMatch = ref.type === 'photo' 
                                     ? (expectations.primary.includes('photo') || expectations.secondary.includes('photo')) 
                                     : (expectations.primary.includes('document') || expectations.secondary.includes('document'));
                                 const isMismatch = !expectedTypeMatch;
                                 return (
                                    <div key={i} className="flex flex-col bg-white border border-blue-200 p-2 rounded text-xs shadow-sm cursor-pointer hover:border-blue-400 transition-colors" onClick={() => setInspectedAssetId(ref.source_id || null)}>
                                        <div className="flex justify-between items-center mb-1">
                                            <div className="flex gap-2 items-center truncate">
                                                <span className="text-sm">{ref.type === 'photo' ? '📷' : '📄'}</span>
                                                <span className="font-bold text-slate-800 truncate">{ref.label}</span>
                                            </div>
                                            <span className={`text-[8px] font-black tracking-widest uppercase px-1.5 py-0.5 flex-shrink-0 rounded border ${ref.support_status === 'missing' ? 'bg-red-50 border-red-200 text-red-700' : 'bg-emerald-50 border-emerald-200 text-emerald-700'}`}>{ref.support_status}</span>
                                        </div>
                                        {isMismatch && (
                                            <div className="text-[8px] uppercase tracking-widest font-black text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded w-max mt-1 relative z-10 flex gap-1">
                                                <span>⚠️</span> Type Mismatch Detection!
                                            </div>
                                        )}
                                    </div>
                                 );
                             })
                         )}
                    </div>
                </div>
            )}

            {/* GLOBALLY RENDERED PHOTOS */}
            {filterBy !== 'docs' && (
                <div>
                    <div className="text-[11px] font-black uppercase tracking-widest text-slate-800 mb-2 border-b border-slate-300 pb-1">
                        Photos
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        {filteredPhotos.length === 0 && <div className="col-span-2 text-xs text-slate-500 italic px-2">No matching photos found</div>}
                        {filteredPhotos.map((p, idx) => {
                            const explicitLinked = photoConfirmations[selectedFinding?.id || ""]?.linked_asset_ids || [];
                            const isSystemLinked = refs.some(r => r.source_id === p.id);
                            const isExplicitLinked = explicitLinked.includes(p.id);
                            const isLinkedToFinding = isSystemLinked || isExplicitLinked;
                            
                            return (
                            <div key={`${p.id}-${idx}`} className="bg-white border shadow-sm rounded overflow-hidden flex flex-col relative group transition-colors cursor-pointer border-slate-200 hover:border-blue-400 hover:ring-1 hover:ring-blue-100" onClick={() => setInspectedAssetId(p.id)}>
                                {(p.is_mock || p.source_kind === 'generated_fixture') && (
                                    <div className="absolute top-0 left-0 right-0 z-10 bg-amber-100/90 backdrop-blur-sm text-amber-800 border-b border-amber-300 text-[8px] font-black uppercase tracking-widest text-center py-0.5">
                                        Mock / Fixture Asset
                                    </div>
                                )}
                                {isSystemLinked && (
                                    <div className="absolute top-2 left-2 z-10 shadow-sm text-[12px] filter drop-shadow" title="Auto-Linked by System">📌</div>
                                )}
                                
                                {selectedFinding && (
                                    <div 
                                        className="absolute top-2 right-2 z-20 cursor-pointer"
                                        onClick={(e) => { e.stopPropagation(); toggleLink(p.id); }}
                                    >
                                        <div className={`w-5 h-5 rounded border shadow-sm flex items-center justify-center transition-all ${isLinkedToFinding ? 'bg-emerald-500 border-emerald-600' : 'bg-white/90 border-slate-300 hover:border-slate-400 hover:bg-white'}`}>
                                            {isLinkedToFinding && <span className="text-white text-[12px] font-bold leading-none select-none">✓</span>}
                                        </div>
                                    </div>
                                )}
                                
                                <div className={`aspect-square bg-slate-100 relative overflow-hidden ${(p.is_mock || p.source_kind === 'generated_fixture') ? 'mt-4' : ''}`}>
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img src={p.thumbnail_url || p.url} alt="Evidence" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                                    {p.confidence && p.confidence > 0 && (
                                        <div className="absolute bottom-1 right-1 bg-black/70 backdrop-blur pointer-events-none text-white text-[8px] uppercase font-black px-1.5 py-0.5 rounded flex gap-2 border border-white/20">
                                            <span className="text-blue-300 truncate max-w-[50px]">{p.damage_area || p.type}</span>
                                            <span className={p.confidence > 0.8 ? "text-emerald-400" : "text-amber-400"}>{(p.confidence * 100).toFixed(0)}% CONF</span>
                                        </div>
                                    )}
                                </div>
                                <div className="px-2 py-1.5 flex justify-between items-center bg-slate-50 border-t border-slate-100">
                                    <div className="flex items-center gap-1 min-w-0">
                                        <StatusBadge status={p.processing_status} />
                                    </div>
                                    <span className="text-xs text-slate-400 group-hover:text-blue-500 transition-colors">↗</span>
                                </div>
                            </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* GLOBALLY RENDERED DOCUMENTS */}
            {filterBy !== 'photos' && (
                <div>
                    <div className="text-[11px] font-black uppercase tracking-widest text-slate-800 mb-2 border-b border-slate-300 pb-1 mt-6">
                        Documents
                    </div>
                    <div className="flex flex-col gap-2">
                        {filteredDocs.length === 0 && <div className="text-xs text-slate-500 italic px-2">No matching documents found</div>}
                        {filteredDocs.map((d, idx) => {
                            const isLinkedToFinding = refs.some(r => r.source_id === d.id);
                            return (
                            <div key={`${d.id}-${idx}`} className="bg-white border shadow-sm rounded flex flex-col relative overflow-hidden transition-colors cursor-pointer border-slate-200 hover:border-blue-400 hover:ring-1 hover:ring-blue-100" onClick={() => setInspectedAssetId(d.id)}>
                                <div className="flex gap-3 p-2 items-stretch group">
                                    {(d.is_mock || d.source_kind === 'generated_fixture') && <div className="absolute top-0 bottom-0 left-0 w-1 bg-amber-400"></div>}
                                    {!d.is_mock && d.source_kind !== 'generated_fixture' && <div className="absolute top-0 bottom-0 left-0 w-1 bg-blue-400"></div>}
                                    
                                    <div className="w-12 h-16 bg-slate-100 border border-slate-200 rounded flex-shrink-0 flex items-center justify-center overflow-hidden ml-1 relative">
                                        {d.thumbnail_url ? (
                                            /* eslint-disable-next-line @next/next/no-img-element */
                                            <img src={d.thumbnail_url} className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity" alt="doc preview"/>
                                        ) : (
                                            <span className="text-xl group-hover:scale-110 transition-transform">📄</span>
                                        )}
                                        {isLinkedToFinding && <div className="absolute top-0.5 left-0.5 z-10 text-[9px] filter drop-shadow">📌</div>}
                                        {(d.is_mock || d.source_kind === 'generated_fixture') && (
                                            <div className="absolute top-0 left-0 right-0 bg-amber-100 text-amber-800 text-[6px] font-black uppercase tracking-widest text-center py-0.5 px-0.5 leading-none">
                                                Mock
                                            </div>
                                        )}
                                    </div>
                                    
                                    <div className="flex-1 flex flex-col justify-between py-0.5 overflow-hidden">
                                        <div className="flex justify-between items-start pr-1">
                                            <div className="text-xs font-bold text-slate-800 truncate max-w-[150px]" title={d.filename}>{d.filename}</div>
                                            <StatusBadge status={d.processing_status} />
                                        </div>
                                        
                                        <div className="flex justify-between items-end mt-1 pr-1">
                                            <div className="flex gap-2 border-t border-slate-100/0 pt-1">
                                                <span className="text-[8px] font-black uppercase tracking-widest text-slate-500 bg-slate-100 px-1 py-0.5 rounded border border-slate-200">{d.doc_type}</span>
                                                {d.confidence && d.confidence > 0 && (
                                                    <span className={`text-[8px] font-black uppercase tracking-widest px-1 py-0.5 rounded border ${d.confidence > 0.8 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                                                        {(d.confidence * 100).toFixed(0)}% CONF
                                                    </span>
                                                )}
                                            </div>
                                            <span className="text-[8px] font-mono text-slate-400 truncate max-w-[60px] group-hover:text-blue-500 transition-colors" title={d.extraction_method}>▶ Details</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Bottom Spacer */}
            <div className="h-10"></div>
        </div>
    );
};
