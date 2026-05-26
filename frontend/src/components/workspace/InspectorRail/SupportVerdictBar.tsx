import React from 'react';

export type AuditorVerdict = 'valid' | 'weak' | 'invalid' | null;

interface SupportVerdictBarProps {
    currentVerdict: AuditorVerdict;
    onVerdictDecision: (v: AuditorVerdict) => void;
    isVisible: boolean;
}

export const SupportVerdictBar: React.FC<SupportVerdictBarProps> = ({ currentVerdict, onVerdictDecision, isVisible }) => {
    if (!isVisible) return null;
    
    return (
        <div className="flex flex-col gap-2 pt-3 border-t border-slate-200 mt-2 bg-slate-50/50 p-2 rounded">
            <div className="font-sans font-black uppercase tracking-widest text-[9px] text-slate-500 border-b border-slate-200 pb-1">
                Auditor Verdict
            </div>
            <div className="grid grid-cols-3 gap-2">
                 <button 
                     onClick={() => onVerdictDecision('valid')}
                     className={`text-[9px] font-black uppercase tracking-widest px-1 py-1.5 rounded shadow-sm border transition-colors flex flex-col items-center justify-center gap-1 focus:ring-2 focus:ring-emerald-200 ${currentVerdict === 'valid' ? 'bg-emerald-700 text-white border-emerald-900 shadow-inner' : 'bg-white text-emerald-800 border-emerald-200 hover:bg-emerald-50'}`}
                 >
                     <span className="text-[12px]">✅</span> Valid Support
                 </button>
                 <button 
                     onClick={() => onVerdictDecision('weak')}
                     className={`text-[9px] font-black uppercase tracking-widest px-1 py-1.5 rounded shadow-sm border transition-colors flex flex-col items-center justify-center gap-1 focus:ring-2 focus:ring-amber-200 ${currentVerdict === 'weak' ? 'bg-amber-600 text-white border-amber-800 shadow-inner' : 'bg-white text-amber-900 border-amber-300 hover:bg-amber-50'}`}
                 >
                     <span className="text-[12px]">⚠️</span> Weak Support
                 </button>
                 <button 
                     onClick={() => onVerdictDecision('invalid')}
                     className={`text-[9px] font-black uppercase tracking-widest px-1 py-1.5 rounded shadow-sm border transition-colors flex flex-col items-center justify-center gap-1 focus:ring-2 focus:ring-slate-200 ${currentVerdict === 'invalid' ? 'bg-slate-700 text-white border-slate-900 shadow-inner' : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'}`}
                 >
                     <span className="text-[12px]">❌</span> Not Relevant
                 </button>
            </div>
            <span className="text-[8px] uppercase tracking-widest font-black text-slate-400 mt-1">Use this to confirm whether the asset actually supports the selected finding.</span>
        </div>
    );
};
