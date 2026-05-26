"use client";
import React from "react";
import { IngestionStatusCard } from "./IngestionStatusCard";
import { EstimateSnapshotCard } from "./EstimateSnapshotCard";
import { ClaimSignalsCard } from "./ClaimSignalsCard";
import { FileInventoryPanel } from "./FileInventoryPanel";

export const ClaimContextRail: React.FC = () => {
    return (
        <div className="flex flex-col w-full h-full p-4 space-y-4">
            <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-black tracking-widest text-slate-500 uppercase">File Context</span>
                <span className="flex-1 h-px bg-slate-200"></span>
            </div>
            
            <IngestionStatusCard />
            <FileInventoryPanel />
            <EstimateSnapshotCard />
            <ClaimSignalsCard />
        </div>
    );
};
