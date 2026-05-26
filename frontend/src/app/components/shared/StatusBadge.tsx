import React from "react";

export const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
    if (!status) return null;
    let style = "bg-slate-100 text-slate-600 border-slate-200";
    if (status === 'cv_complete') style = "bg-blue-50 text-blue-700 border-blue-200";
    if (status === 'cv_pending') style = "bg-purple-50 text-purple-700 border-purple-200";
    if (status === 'mapped') style = "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (status === 'failed') style = "bg-red-50 text-red-700 border-red-200";
    if (status === 'uploaded') style = "bg-slate-50 text-slate-600 border-slate-200";
    if (status === 'preview_ready') style = "bg-indigo-50 text-indigo-700 border-indigo-200";
    if (status === 'complete') style = "bg-emerald-50 text-emerald-700 border-emerald-200";

    return (
        <span className={`text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded border shadow-sm ${style}`}>
            {status.replace('_', ' ')}
        </span>
    );
};
