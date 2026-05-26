"use client";
import React, { useState } from "react";
import { useAuditData } from "../AuditContext";
import { generateMarkdownExport } from "@/lib/exportUtils";

export const BottomUtilityTray: React.FC = () => {
    const [activeTab, setActiveTab] = useState("activity");
    const { auditRun } = useAuditData();

    // Export Generation Logic (uses shared utility)
    const exportText = auditRun ? generateMarkdownExport(auditRun) : "Waiting for audit data...";

    return (
        <div className="flex flex-col w-full h-full text-slate-700 bg-white">
            <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-6">
                <div className="flex items-center">
                    {[
                        { id: "activity", label: "Activity Log" },
                        { id: "history", label: "Audit History" },
                        { id: "trace", label: "Rule Trace" },
                        { id: "export", label: "Export Preview" }
                    ].map(t => (
                        <button
                            key={t.id}
                            onClick={() => setActiveTab(t.id)}
                            className={`px-4 py-3 border-b-2 text-[10px] uppercase font-black tracking-widest ${
                                activeTab === t.id ? 'border-blue-600 text-blue-700 bg-white shadow-[0_-2px_5px_rgba(0,0,0,0.02)]' : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                            }`}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
            </div>
            
            <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
                {activeTab === "activity" && (
                    <div className="w-full max-w-4xl">
                        <div className="flex flex-col gap-4 relative py-2">
                            <div className="absolute left-3.5 top-2 bottom-2 w-px bg-slate-200" />
                            
                            {auditRun?.activity_log?.map((evt, idx) => {
                                const d = new Date(evt.timestamp);
                                const timeStr = d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                                const isSystem = evt.actor === 'system';
                                
                                return (
                                    <div key={evt.id || idx} className="relative pl-8 pr-2">
                                        <div className={`absolute left-2.5 top-1.5 w-2.5 h-2.5 rounded-full border-2 border-white z-10 ${isSystem ? 'bg-blue-500' : 'bg-purple-500'}`} />
                                        <div className="flex flex-col gap-1">
                                            <div className="flex items-center gap-2">
                                                <span className="text-[9px] font-mono text-slate-500 bg-slate-100 px-1 rounded border border-slate-200">{timeStr}</span>
                                                <span className={`text-[9px] font-black uppercase tracking-widest ${isSystem ? 'text-blue-600' : 'text-purple-600'}`}>
                                                    {evt.actor} • {evt.event_type.replace('_', ' ')}
                                                </span>
                                            </div>
                                            <div className="text-xs text-slate-800">
                                                {evt.description}
                                            </div>
                                            {evt.metadata_context?.comment && (
                                                <div className="mt-1 text-xs text-slate-600 italic border-l-2 border-slate-300 pl-2 bg-slate-50 py-1 rounded-r w-max pr-4">
                                                    "{evt.metadata_context.comment}"
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                            
                            {(!auditRun?.activity_log || auditRun.activity_log.length === 0) && (
                                <div className="italic text-slate-500 text-center p-6 border border-dashed border-slate-300 rounded bg-slate-50 text-xs mt-2 mx-4">
                                    No activity recorded.
                                </div>
                            )}
                        </div>
                    </div>
                )}
                
                {activeTab === "history" && (
                    <div className="text-xs text-slate-600 max-w-2xl">
                        <div className="font-bold text-slate-900 mb-2 uppercase text-[10px] tracking-widest">Version Timeline</div>
                        <ul className="space-y-2 border-l border-slate-300 pl-3">
                            <li><span className="text-slate-500 font-mono">10:05 AM</span> - System AI parsed CCC/EMS, mapped evidence.</li>
                            <li><span className="text-slate-500 font-mono">10:06 AM</span> - Scoring Module generated initial severity 86/100.</li>
                        </ul>
                    </div>
                )}
                
                {activeTab === "trace" && (
                    <div className="text-xs text-slate-600 max-w-4xl">
                        <div className="font-bold text-slate-900 mb-2 uppercase text-[10px] tracking-widest">Execution Path</div>
                        <div className="bg-slate-50 border border-slate-200 p-3 rounded font-mono text-[10px] text-slate-700 whitespace-pre shadow-sm">
                            {`> [RulesEngine] Loading NatGen profiles...
> [RulesEngine] Checking Line 8...
> [EvidenceMap] Querying scan documentation...
> [EvidenceMap] Returned 0 documents.
> [RulesEngine] TRIGGERED "NATGEN_001". Confidence: 0.92`}
                        </div>
                    </div>
                )}
                
                {activeTab === "export" && (
                    <div className="flex flex-col gap-4 max-w-4xl h-full">
                        <div className="flex justify-between items-center bg-blue-50 border border-blue-200 p-3 rounded shadow-sm">
                            <div className="flex flex-col">
                                <span className="text-[10px] font-black uppercase tracking-widest text-blue-800">Export Payload Ready</span>
                                <span className="text-xs text-slate-600">Use this structured markdown to drop into CMS or claim notes.</span>
                            </div>
                            <button 
                                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-[10px] font-black uppercase tracking-widest rounded text-white shadow-sm transition-all"
                                onClick={() => navigator.clipboard.writeText(exportText)}
                            >
                                Copy to Clipboard
                            </button>
                        </div>
                        <textarea 
                            readOnly
                            className="flex-1 w-full min-h-[300px] bg-white border border-slate-300 rounded p-4 text-xs font-mono text-slate-800 resize-none outline-none custom-scrollbar shadow-sm"
                            value={exportText}
                        />
                    </div>
                )}
            </div>
        </div>
    );
};
