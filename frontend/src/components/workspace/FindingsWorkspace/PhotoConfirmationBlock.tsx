"use client";
import React from "react";
import { Finding } from "@/types/claim";
import { useAudit } from "../AuditContext";
import { getExpectedSupportTypes } from "@/lib/evidenceAssessment";

interface Props {
    finding: Finding;
}

export const PhotoConfirmationBlock: React.FC<Props> = ({ finding }) => {
    const { photoConfirmations, savePhotoConfirmation } = useAudit();
    const expectations = getExpectedSupportTypes(finding.category);
    
    // Only render if photos are expected
    if (!expectations.primary.includes('photo')) {
        return null;
    }

    const state = photoConfirmations[finding.id] || {};

    return (
        <div className="bg-slate-50 border border-slate-200 rounded p-3 space-y-3 shadow-inner" onClick={e => e.stopPropagation()}>
            <h4 className="text-[10px] uppercase font-black text-slate-700 tracking-widest border-b border-slate-200 pb-1">
                Photo Evidence Confirmation
            </h4>
            
            <div className="space-y-2 text-xs">
                <div className="flex flex-col gap-1">
                    <label className="font-bold text-slate-800">1. Are there photos showing this damage?</label>
                    <select 
                        value={state.evidence_exists || ""} 
                        onChange={(e) => savePhotoConfirmation(finding.id, { evidence_exists: e.target.value as any })}
                        className="p-1.5 border border-slate-300 rounded bg-white focus:ring-1 focus:ring-blue-300 outline-none text-slate-700 w-full"
                    >
                        <option value="" disabled>Select option...</option>
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                        <option value="unknown">Unknown / Pending</option>
                    </select>
                </div>

                {state.evidence_exists === 'yes' && (
                    <div className="flex flex-col gap-1 pt-2">
                        <label className="font-bold text-slate-800">2. Are those photos included in this file?</label>
                        <select 
                            value={state.evidence_uploaded || ""} 
                            onChange={(e) => savePhotoConfirmation(finding.id, { evidence_uploaded: e.target.value as any })}
                            className="p-1.5 border border-slate-300 rounded bg-white focus:ring-1 focus:ring-blue-300 outline-none text-slate-700 w-full"
                        >
                            <option value="" disabled>Select option...</option>
                            <option value="yes">Yes</option>
                            <option value="no">No</option>
                        </select>
                    </div>
                )}
                
                {state.evidence_exists === 'yes' && state.evidence_uploaded === 'no' && (
                    <div className="flex flex-col gap-1 pt-2">
                        <label className="font-bold text-slate-800">Why are they missing?</label>
                        <select 
                            value={state.missing_upload_reason || ""} 
                            onChange={(e) => savePhotoConfirmation(finding.id, { missing_upload_reason: e.target.value })}
                            className="p-1.5 border border-slate-300 rounded bg-white focus:ring-1 focus:ring-blue-300 outline-none text-slate-700 w-full"
                        >
                            <option value="" disabled>Select reason...</option>
                            <option value="shop_has_photos">Shop states they have photos</option>
                            <option value="ia_did_not_upload">IA did not upload</option>
                            <option value="supplement_pending">Pending supplement</option>
                            <option value="photos_requested">Photos requested</option>
                            <option value="other">Other (explain in note)</option>
                        </select>
                    </div>
                )}

                {state.evidence_exists === 'yes' && state.evidence_uploaded === 'yes' && (
                    <div className="flex flex-col gap-1 pt-2 border-t border-slate-200 mt-2">
                        <label className="font-bold text-emerald-800">3. Select supporting photo(s)</label>
                        <div className="text-[10px] text-slate-600 leading-tight">
                            Navigate to the <strong className="font-black text-slate-800">Evidence Panel</strong> (Press '2') and check the box on photos that support this finding.
                        </div>
                        <div className="flex items-center gap-2 mt-1 py-1">
                            <span className={`px-2 py-0.5 border rounded text-[9px] font-black uppercase tracking-widest ${
                                (state.linked_asset_ids?.length || 0) > 0 
                                ? 'bg-emerald-100 text-emerald-800 border-emerald-300' 
                                : 'bg-slate-100 text-slate-500 border-slate-300'
                            }`}>
                                {(state.linked_asset_ids?.length || 0)} Linked Photos
                            </span>
                            {(!state.linked_asset_ids || state.linked_asset_ids.length === 0) && (
                                <span className="text-[9px] text-red-600 font-bold uppercase tracking-widest flex items-center gap-1">
                                    <span className="text-xs">⚠️</span> Action Required
                                </span>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
