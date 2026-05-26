import React from 'react';
import { SupportQuality } from '@/lib/evidenceAssessment';

export const SupportQualityBadge: React.FC<{ quality: SupportQuality }> = ({ quality }) => {
    if (quality === 'UNSCORED') return null;
    
    let colorClass = '';
    let description = '';
    
    switch (quality) {
        case 'STRONG':
            colorClass = 'bg-emerald-50 border-emerald-300 text-emerald-800';
            description = 'Asset linkage and type aligns strongly with selected finding.';
            break;
        case 'WEAK':
            colorClass = 'bg-amber-50 border-amber-300 text-amber-800';
            description = 'Asset may be vaguely relevant, but confidence or explicit linkage is limited.';
            break;
        case 'INVALID':
            colorClass = 'bg-red-50 border-red-300 text-red-800';
            description = 'Linked asset does not adequately support the selected finding context.';
            break;
    }
    
    return (
        <div className={`p-3 border rounded shadow-sm ${colorClass} flex flex-col gap-1`}>
            <div className="flex items-center gap-2">
                <span className="font-black text-[11px] uppercase tracking-widest bg-white/50 px-2 py-0.5 rounded border border-black/5">SUPPORT QUALITY: {quality}</span>
            </div>
            <div className="text-xs font-bold font-sans mt-1 opacity-90">{description}</div>
        </div>
    );
};
