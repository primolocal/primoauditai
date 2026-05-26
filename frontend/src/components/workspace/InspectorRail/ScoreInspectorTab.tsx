"use client";
import React from "react";
import { useAuditData } from "../AuditContext";

export const ScoreInspectorTab: React.FC = () => {
    const { auditRun, selectedFinding } = useAuditData();
    const sc = auditRun?.scorecard;
    if (!sc) return null;

    return (
        <div className="space-y-6">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 pb-1 border-b border-slate-200">
                Audit Integrity Score
            </div>
            
            <div className="flex items-center justify-center py-6">
                <div className="relative flex items-center justify-center w-32 h-32 rounded-full border-[8px] border-slate-100 bg-white shadow-sm">
                    <div className="absolute inset-0 rounded-full border-[8px] border-red-400" style={{ clipPath: 'polygon(0 0, 100% 0, 100% 70%, 0 70%)' }}></div>
                    <div className="flex flex-col items-center">
                        <span className="text-4xl font-black text-slate-900 leading-none">{sc.overall_score}</span>
                        <span className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mt-1">{sc.verdict}</span>
                    </div>
                </div>
            </div>

            {selectedFinding && selectedFinding.status !== 'overturned' && (
                <div className="bg-white border border-slate-200 shadow-sm rounded p-3 flex items-start gap-3">
                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] font-black uppercase tracking-widest text-blue-600">Finding Impact</span>
                        <p className="text-xs text-slate-600">
                            This <span className="font-bold uppercase text-slate-900">{selectedFinding.severity}</span> level finding penalizes the <span className="font-bold text-slate-900 uppercase">{selectedFinding.category.replace(/_/g, ' ')}</span> score. Overturning it will restore these points.
                        </p>
                    </div>
                </div>
            )}

            <div>
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3 border-b border-slate-200 pb-1">
                    Category Breakdown
                </div>
                
                <div className="space-y-4">
                    {Object.entries(sc.category_scores).map(([k, v]) => {
                        const isTarget = selectedFinding?.category === k;
                        return (
                        <div key={k} className={`flex flex-col gap-1 ${isTarget ? 'bg-blue-50 -mx-2 px-2 py-1.5 rounded border border-blue-200' : ''}`}>
                            <div className="flex justify-between items-center">
                                <span className={`text-xs uppercase tracking-wider font-bold ${isTarget ? 'text-blue-700' : 'text-slate-700'}`}>{k.replace(/_/g, ' ')}</span>
                                <span className={`text-[10px] font-mono font-bold ${v < 80 ? 'text-red-600' : 'text-emerald-600'}`}>{v}/100</span>
                            </div>
                            <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                <div className={`h-full ${v < 80 ? 'bg-red-500' : 'bg-emerald-500'} ${isTarget ? 'brightness-110' : ''}`} style={{ width: `${v}%` }}></div>
                            </div>
                        </div>
                    )})}
                </div>
            </div>
        </div>
    );
};
