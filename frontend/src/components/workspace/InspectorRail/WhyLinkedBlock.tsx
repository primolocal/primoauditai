import React from 'react';

export const WhyLinkedBlock: React.FC<{ reasons: string[] }> = ({ reasons }) => {
    return (
        <div className="flex flex-col gap-2 text-[10px] font-mono mt-1 pt-3 border-t border-slate-200">
            <div className="font-sans font-black uppercase tracking-widest text-[9px] text-slate-500 mb-1">
                Why This Asset Is Linked
            </div>
            <ul className="flex flex-col gap-1.5 list-disc pl-4 text-slate-700">
                {reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                ))}
            </ul>
        </div>
    );
};
