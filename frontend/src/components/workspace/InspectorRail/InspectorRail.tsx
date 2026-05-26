"use client";
import React from "react";
import { useAuditInteraction } from "../AuditContext";
import { EstimateInspectorTab } from "./EstimateInspectorTab";
import { EvidenceInspectorTab } from "./EvidenceInspectorTab";
import { ScoreInspectorTab } from "./ScoreInspectorTab";
import { NarrativeInspectorTab, ReviewerActionTab } from "./EditorTabs";

export const InspectorRail: React.FC = () => {
    const { activeInspectorTab, setActiveInspectorTab, selectedFindingId } = useAuditInteraction();
    
    const tabs = [
        { id: "estimate", label: "Estimate Detail" },
        { id: "evidence", label: "Evidence" },
        { id: "score", label: "Score" },
        { id: "narrative", label: "Narrative" },
        { id: "action", label: "Action" }
    ];

    return (
        <div className="flex flex-col w-full h-full bg-white">
            {/* Tab Header Group */}
            <div className="flex w-full items-center border-b border-slate-200 overflow-x-auto custom-scrollbar bg-slate-50 px-2 pt-2">
                {tabs.map(t => (
                    <button
                        key={t.id}
                        onClick={() => setActiveInspectorTab(t.id)}
                        className={`px-4 py-3 border-b-2 text-[10px] font-black uppercase tracking-widest whitespace-nowrap transition-colors ${
                            activeInspectorTab === t.id 
                            ? 'border-blue-600 text-blue-700 bg-white shadow-[0_-2px_5px_rgba(0,0,0,0.02)]' 
                            : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                        }`}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {/* Content Area */}
            <div className="flex-1 p-6 overflow-y-auto">
                {!selectedFindingId && activeInspectorTab !== "score" && activeInspectorTab !== "narrative" && activeInspectorTab !== "evidence" ? (
                    <div className="text-sm text-slate-500 text-center mt-12 italic border border-dashed border-slate-300 p-8 rounded bg-slate-50">
                        Select a finding in the center panel to inspect related evidence and logic.
                    </div>
                ) : (
                    <div className="text-slate-700 text-sm">
                        {activeInspectorTab === "estimate" && <EstimateInspectorTab />}
                        {activeInspectorTab === "evidence" && <EvidenceInspectorTab />}
                        {activeInspectorTab === "score" && <ScoreInspectorTab />}
                        {activeInspectorTab === "narrative" && <NarrativeInspectorTab />}
                        {activeInspectorTab === "action" && <ReviewerActionTab />}
                    </div>
                )}
            </div>
        </div>
    );
};
