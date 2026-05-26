"use client";

import React, { useState } from "react";
import { AuditHeader } from "./AuditHeader";
import { ClaimContextRail } from "./ClaimContextRail/ClaimContextRail";
import { FindingsWorkspace } from "./FindingsWorkspace/FindingsWorkspace";
import { InspectorRail } from "./InspectorRail/InspectorRail";
import { BottomUtilityTray } from "./UtilityTray/BottomUtilityTray";
import { useAuditData } from "./AuditContext";
import { UploadHarness } from "./UploadHarness";

export const AuditWorkbench: React.FC = () => {
  const [trayOpen, setTrayOpen] = useState(false);
  const { auditRun } = useAuditData();
  
  if (!auditRun) {
      return <UploadHarness />;
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-50 text-slate-900 font-sans antialiased">
      {/* 1. Top Header Bar (Fixed) */}
      <div className="flex-none h-16 border-b border-slate-200 bg-white z-10 shadow-sm relative">
        <AuditHeader />
      </div>

      {/* Main 3-Column Layout Workspace */}
      <div className="flex flex-1 overflow-hidden">
        {/* 2. Left Column: Claim Context + File Intake (width: 20-25%) */}
        <div className="w-1/4 min-w-[300px] max-w-[400px] border-r border-slate-200 bg-slate-50/50 overflow-y-auto custom-scrollbar hidden md:block">
           <ClaimContextRail />
        </div>

        {/* 3. Center Column: Findings Worklist (width: 45-50%) */}
        <div className="flex-1 min-w-[500px] bg-slate-50 overflow-y-auto custom-scrollbar">
           <FindingsWorkspace />
        </div>

        {/* 4. Right Column: Evidence + Estimate Inspector (width: 25-30%) */}
        <div className="w-[30%] min-w-[400px] max-w-[600px] border-l border-slate-200 bg-white overflow-y-auto custom-scrollbar hidden lg:block">
           <InspectorRail />
        </div>
      </div>

      {/* 5. Bottom Utility Tray (Collapsible) */}
      {trayOpen && (
        <div className="flex-none h-64 border-t border-slate-200 bg-white overflow-y-auto custom-scrollbar z-20 transition-all duration-300 shadow-[0_-5px_15px_rgba(0,0,0,0.05)]">
           <BottomUtilityTray />
        </div>
      )}
      <div 
         className="flex-none h-8 bg-slate-100 border-t border-slate-200 flex items-center justify-center cursor-pointer hover:bg-slate-200 transition-colors z-20 select-none"
         onClick={() => setTrayOpen(!trayOpen)}
      >
        <span className="text-xs font-semibold tracking-wider text-slate-500">
            {trayOpen ? "CLOSE UTILITY TRAY" : "OPEN UTILITY TRAY (HISTORY & TRACE)"}
        </span>
      </div>
    </div>
  );
};
