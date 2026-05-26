import React from 'react';
import { useAudit } from '../AuditContext';
import { NormalizedDocument, PhotoEvidence, Finding, EvidenceRef } from '@/types/claim';
import { getSupportQuality, buildLinkReasoning, getExpectedSupportTypes, SupportQuality } from '@/lib/evidenceAssessment';
import { SupportQualityBadge } from './SupportQualityBadge';
import { WhyLinkedBlock } from './WhyLinkedBlock';
import { SupportVerdictBar, AuditorVerdict } from './SupportVerdictBar';
import { StatusBadge } from '@/app/components/shared/StatusBadge';

interface AssetDetailPanelProps {
    asset: NormalizedDocument | PhotoEvidence;
    sequence: (NormalizedDocument | PhotoEvidence)[];
    selectedFinding: Finding | null;
    refs: EvidenceRef[];
    setInspectedAssetId: (id: string | null) => void;
}

export const AssetDetailPanel: React.FC<AssetDetailPanelProps> = ({ asset, sequence, selectedFinding, refs, setInspectedAssetId }) => {
    // Global Verdict State
    const stateKey = selectedFinding ? `${selectedFinding.id}_${asset.id}` : null;
    const { verdictStore, saveAssetVerdict } = useAudit();
    
    const currentVerdict = stateKey ? (verdictStore[stateKey] || null) : null;
    const handleVerdict = (v: AuditorVerdict) => {
        if (!stateKey) return;
        saveAssetVerdict(stateKey, v);
    };

    const isPhoto = 'type' in asset;
    const currentIndex = sequence.findIndex(a => a.id === asset.id);
    const hasPrev = currentIndex > 0;
    const hasNext = currentIndex < sequence.length - 1;
    
    const isLinkedToFinding = refs.some(r => r.source_id === asset.id);
    const refMatch = refs.find(r => r.source_id === asset.id);
    
    const expectations = getExpectedSupportTypes(selectedFinding?.category);
    const expectedTypeMatch = isPhoto 
        ? (expectations.primary.includes('photo') || expectations.secondary.includes('photo')) 
        : (expectations.primary.includes('document') || expectations.secondary.includes('document'));
    const isMismatch = isLinkedToFinding && !expectedTypeMatch;
    const isLowConfidence = asset.confidence !== undefined && asset.confidence < 0.7;

    const supportQuality = getSupportQuality(asset, selectedFinding, refs);
    const reasons = buildLinkReasoning(asset, selectedFinding, refs);

    const getDisagreementState = (quality: SupportQuality, verdict: AuditorVerdict) => {
        if (!verdict) return 'Needs Review';
        if (quality === 'STRONG' && verdict === 'valid') return 'Aligned';
        if (quality === 'WEAK' && verdict === 'weak') return 'Aligned';
        if (quality === 'INVALID' && verdict === 'invalid') return 'Aligned';
        return 'Reviewer Overrode System';
    };
    const disagreementState = getDisagreementState(supportQuality, currentVerdict);

    const hasPrimaryEvidence = sequence.some(a => {
        const t = 'type' in a ? 'photo' : 'document';
        return expectations.primary.includes(t);
    });
    const showMissingEvidence = selectedFinding && expectations.primary.length > 0 && !hasPrimaryEvidence;

    return (
        <div className="flex flex-col h-full space-y-4 animate-in fade-in slide-in-from-right-4 duration-200">
            {/* 1. Back to Evidence List */}
            <div className="flex justify-between items-center bg-slate-50 p-2 rounded border border-slate-200 shadow-sm sticky top-0 z-20">
                <button 
                    onClick={() => setInspectedAssetId(null)}
                    className="text-[10px] font-black uppercase tracking-widest text-slate-600 hover:text-blue-700 flex items-center gap-1 transition-colors"
                >
                    <span>◀</span> BACK TO LIST
                </button>
                <div className="flex items-center gap-2">
                     <span className="text-[9px] font-black text-slate-400 font-mono">{currentIndex + 1} OF {sequence.length}</span>
                </div>
            </div>

            {/* 2. Large Preview Area */}
            <div className="relative bg-slate-100 border border-slate-200 rounded overflow-hidden flex items-center justify-center min-h-[250px] shadow-sm">
                {(asset.is_mock || asset.source_kind === 'generated_fixture') && (
                    <div className="absolute top-0 left-0 right-0 z-10 bg-amber-100/90 backdrop-blur-sm text-amber-800 border-b border-amber-300 text-[9px] font-black uppercase tracking-widest text-center py-1">
                        Mock / Fixture Asset
                    </div>
                )}
                {isPhoto ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img src={asset.url} alt="Expanded evidence" className="w-full h-full object-contain max-h-[400px]" />
                ) : (
                    <div className="flex flex-col items-center gap-3 p-8">
                        <span className="text-5xl drop-shadow-sm">📄</span>
                        <span className="text-xs font-bold text-slate-600 uppercase tracking-widest border border-slate-200 bg-white px-2 py-1 rounded shadow-sm">DOCUMENT PREVIEW_READY</span>
                    </div>
                )}
            </div>

            {/* 3. Asset Title / Filename */}
            <div className="flex flex-col border-b border-slate-200 pb-2">
                <span className="text-[9px] uppercase tracking-widest font-black text-slate-400">Asset Record</span>
                <span className="font-bold text-slate-800 text-sm truncate" title={'filename' in asset ? asset.filename : asset.id}>{'filename' in asset ? asset.filename : asset.id}</span>
            </div>

            {/* 4. Support Quality & 5. Why Linked & 6. Verdict */}
            <div className="flex flex-col gap-2">
                <SupportQualityBadge quality={supportQuality} />
                <WhyLinkedBlock reasons={reasons} />
                <SupportVerdictBar 
                    currentVerdict={currentVerdict} 
                    onVerdictDecision={handleVerdict} 
                    isVisible={!!selectedFinding} 
                />
                {!!selectedFinding && (
                    <div className="flex items-center justify-between text-[9px] font-black uppercase tracking-widest px-2 py-1.5 bg-slate-100/80 rounded border border-slate-200 mt-1 shadow-sm">
                        <span className="text-slate-500">System vs Auditor Alignment:</span>
                        <span className={`${disagreementState === 'Aligned' ? 'text-emerald-700 font-bold' : disagreementState === 'Needs Review' ? 'text-slate-400' : 'text-amber-700 font-bold'}`}>
                            {disagreementState}
                        </span>
                    </div>
                )}
            </div>

            {/* 7, 8, 9. Metadata grids */}
            <div className="grid grid-cols-2 gap-4 border-t border-slate-200 pt-4">
                {/* Primary Metadata & Provenance */}
                <div className="flex flex-col gap-2 text-[10px] font-mono border-r border-slate-100 pr-4">
                    <div className="font-sans font-black uppercase tracking-widest text-[9px] text-slate-500 mb-1">Primary Metadata</div>
                    <div className="flex flex-col"><span className="text-slate-400">Processing Stage</span><div className="mt-1 flex"><StatusBadge status={asset.processing_status} /></div></div>
                    <div className="flex justify-between mt-2 pt-2 border-t border-slate-100"><span className="text-slate-400">Ext. Method:</span><span className="font-bold text-slate-700 truncate max-w-[80px]">{asset.extraction_method || 'unknown'}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">Source Payload:</span><span className="font-bold text-slate-700 truncate max-w-[80px]">{asset.source_kind || 'internal'}</span></div>
                    <div className="flex flex-col mt-1"><span className="text-slate-400">Ingested At:</span><span className="text-slate-700 bg-slate-50 px-1 mt-0.5 rounded border border-slate-200">{asset.ingested_at ? new Date(asset.ingested_at).toLocaleString() : 'missing time context'}</span></div>
                </div>

                {/* CV Analysis Block */}
                <div className="flex flex-col gap-2 text-[10px] font-mono pl-2">
                    <div className="font-sans font-black uppercase tracking-widest text-[9px] text-slate-500 mb-1">Computer Vision Analysis</div>
                    
                    {(asset.confidence === undefined || asset.confidence === 0) ? (
                        <div className="italic text-slate-400 font-sans p-2 border border-dashed border-slate-200 rounded mt-1">
                            No deterministic CV signature detected for this asset frame.
                        </div>
                    ) : (
                        <>
                            <div className="flex flex-col"><span className="text-slate-400">Class Label</span><span className="font-bold text-slate-800 uppercase px-1 bg-slate-100 rounded border border-slate-200 w-max mt-0.5">{isPhoto ? (asset as PhotoEvidence).damage_area || asset.type : (asset as NormalizedDocument).doc_type}</span></div>
                            
                            <div className="flex flex-col mt-2">
                                <span className="text-slate-400 mb-1">Confidence Score</span>
                                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden border border-slate-200">
                                    <div 
                                        className={`h-full ${isLowConfidence ? 'bg-amber-400' : 'bg-emerald-500'}`} 
                                        style={{ width: `${(asset.confidence || 0) * 100}%` }}
                                    />
                                </div>
                                <span className={`text-right mt-1 font-black ${isLowConfidence ? 'text-amber-600' : 'text-emerald-700'}`}>
                                    {((asset.confidence || 0) * 100).toFixed(1)}% {isLowConfidence ? '(LOW CONFIDENCE)' : ''}
                                </span>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* 10. Context Links & Missing Evidence */}
            <div className="flex flex-col gap-2 border-t border-slate-200 pt-4">
                {showMissingEvidence && (
                    <div className="bg-red-50 border border-red-200 text-red-800 p-3 rounded text-xs shadow-sm mb-2">
                        <div className="font-black uppercase tracking-widest text-[9px] flex items-center gap-1.5 mb-1.5 border-b border-red-200/50 pb-1 w-max">
                            <span>❌</span> Missing Expected Evidence
                        </div>
                        <div className="pl-1 italic opacity-90 leading-tight">
                            The '{selectedFinding.category.replace(/_/g, ' ')}' category requires {expectations.primary.join(' or ')} support. <br/>
                            <span className="font-bold">No qualifying {expectations.primary.join(' or ')} evidence was detected anywhere in the entire claim.</span>
                        </div>
                    </div>
                )}

                {/* Linked Context Warning */}
                <div className={`p-3 rounded border text-xs shadow-sm ${isLinkedToFinding ? 'bg-blue-50 border-blue-200' : 'bg-slate-50 border-slate-200'}`}>
                    <div className="flex items-center gap-2 font-black uppercase tracking-widest text-[9px] mb-1">
                        {isLinkedToFinding ? (
                            <><span className="text-blue-700">📌 Linked to Selected Finding</span><span className={`px-1.5 py-0.5 rounded border ${refMatch?.support_status === 'missing' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>{refMatch?.support_status}</span></>
                        ) : (
                            <span className="text-slate-500">Unlinked Global Asset</span>
                        )}
                    </div>
                    {isLinkedToFinding && refMatch?.reason && (
                        <div className="text-blue-900 border-l-2 border-blue-300 pl-2 mt-2 italic">{refMatch.reason}</div>
                    )}
                    {isMismatch && (
                        <div className="text-[9px] mt-2 uppercase tracking-widest font-black text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded flex gap-1 w-max">
                            <span>⚠️</span> Type Mismatch Detection!
                        </div>
                    )}
                </div>
            </div>

            {/* 11. Next/Previous Controls */}
            <div className="flex justify-between items-center pt-2 pb-6 border-t border-slate-200 mt-4">
                <button 
                    disabled={!hasPrev} 
                    onClick={() => setInspectedAssetId(sequence[currentIndex - 1].id)}
                    className="px-3 py-1.5 text-[10px] uppercase tracking-widest font-black bg-white border border-slate-200 rounded text-slate-600 disabled:opacity-30 shadow-sm hover:bg-slate-50 transition-colors"
                >◀ Previous Asset</button>
                <button 
                    disabled={!hasNext} 
                    onClick={() => setInspectedAssetId(sequence[currentIndex + 1].id)}
                    className="px-3 py-1.5 text-[10px] uppercase tracking-widest font-black bg-white border border-slate-200 rounded text-slate-600 disabled:opacity-30 shadow-sm hover:bg-slate-50 transition-colors"
                >Next Asset ▶</button>
            </div>
            
            <div className="h-10 shrink-0"></div>
        </div>
    );
};
