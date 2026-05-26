"use client";
import React, { useState } from "react";
import { useAuditData } from "./AuditContext";
import { generateMarkdownExport } from "@/lib/exportUtils";

export const AuditHeader: React.FC = () => {
  const { auditRun } = useAuditData();
  const [isExportOpen, setIsExportOpen] = useState(false);
  if (!auditRun) return <div className="p-4 text-xs">Waiting for Audit Data...</div>;

  // Derive counts from mock findings
  const criticalCount = auditRun.findings.filter(f => f.severity === "critical" || f.severity === "high").length;
  const majorCount = auditRun.findings.filter(f => f.severity === "major" || f.severity === "medium").length;
  const minorCount = auditRun.findings.filter(f => f.severity === "minor" || f.severity === "low").length;
  const reviewCount = auditRun.findings.filter(f => f.status === "open").length;

  const exportText = generateMarkdownExport(auditRun);

  return (
    <div className="flex w-full h-full items-center justify-between px-6 bg-white border-b border-slate-200 text-slate-800">
      
      {/* 1. LEFT: Claim Meta */}
      <div className="flex flex-col md:flex-row items-start md:items-center gap-2 md:gap-6">
        <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-0.5">Claim Number</span>
            <span className="font-mono text-base font-black text-slate-900 leading-none">{auditRun.claim_package.claim_number}</span>
        </div>
        <div className="hidden md:block w-px h-6 bg-slate-200"></div>
        <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-0.5">Carrier</span>
            <span className="text-sm font-bold text-slate-800 leading-none">{auditRun.claim_package.carrier}</span>
        </div>
        <div className="hidden md:block w-px h-6 bg-slate-200"></div>
        <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 border text-[10px] uppercase font-bold tracking-wider rounded ${
                auditRun.status === 'completed' ? 'bg-emerald-50 border-emerald-200 text-emerald-700' :
                auditRun.status === 'in_review' ? 'bg-blue-50 border-blue-200 text-blue-700' :
                auditRun.status === 'not_started' ? 'bg-white border-slate-200 text-slate-500' :
                'bg-amber-50 border-amber-200 text-amber-700'
            }`}>
                {auditRun.status.replace('_', ' ')}
            </span>
            {auditRun.active_supplement !== "E01" && (
                <span className="px-2 py-0.5 bg-purple-50 border border-purple-200 text-purple-700 text-[10px] uppercase font-bold tracking-wider rounded">
                    {auditRun.active_supplement} Scope
                </span>
            )}
        </div>
        <div className="hidden md:block w-px h-6 bg-slate-200"></div>
        <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-0.5">Vehicle</span>
            <span className="text-xs text-slate-600 font-mono">
                {auditRun.vehicle_profile?.year} {auditRun.vehicle_profile?.make} {auditRun.vehicle_profile?.model}
            </span>
        </div>
      </div>

      {/* 2. CENTER: Completeness & Score Wrapper */}
      <div className="flex items-center gap-8">
         <div className="flex flex-col items-center">
            <span className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">Evidence Mapping</span>
            <span className={`px-2.5 py-0.5 border rounded text-[10px] font-bold uppercase tracking-widest shadow-sm ${
                auditRun.evidence_matrix?.processing_status === 'complete' 
                   ? 'border-blue-200 text-blue-700 bg-blue-50' 
                   : 'border-amber-200 text-amber-700 bg-amber-50 animate-pulse'
            }`}>
               {auditRun.evidence_matrix?.processing_status === 'complete' ? 'MAPPED' : 'PROCESSING...'}
            </span>
         </div>
         
         <div className="flex items-center gap-3 border-l border-r border-slate-200 px-6">
            <div className="flex flex-col items-center">
                <span className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-0.5">Score</span>
                <span className={`text-2xl font-black leading-none ${auditRun.scorecard.overall_score >= 85 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {auditRun.scorecard.overall_score}
                </span>
            </div>
         </div>

         {/* Severity Counts Mini-dash */}
         <div className="flex gap-4">
             <div className="flex flex-col items-center">
                <span className="text-[10px] font-bold text-red-600">{criticalCount}</span>
                <span className="text-[8px] uppercase tracking-widest text-slate-500">Crit</span>
             </div>
             <div className="flex flex-col items-center">
                <span className="text-[10px] font-bold text-amber-600">{majorCount}</span>
                <span className="text-[8px] uppercase tracking-widest text-slate-500">Maj</span>
             </div>
             <div className="flex flex-col items-center">
                <span className="text-[10px] font-bold text-blue-600">{minorCount}</span>
                <span className="text-[8px] uppercase tracking-widest text-slate-500">Min</span>
             </div>
             <div className="flex flex-col items-center">
                <span className="text-[10px] font-bold text-slate-700">{reviewCount}</span>
                <span className="text-[8px] uppercase tracking-widest text-slate-500">Needs Rev</span>
             </div>
         </div>
      </div>

      {/* 3. RIGHT: Actions */}
      <div className="flex items-center gap-3">
         <div className="flex flex-col text-right mr-4">
             <span className="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Auditor</span>
             <span className="text-xs font-bold text-slate-800">T. Reviewer</span>
         </div>
         <button className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 hover:text-slate-900 active:scale-95 text-xs font-bold uppercase tracking-widest rounded text-slate-700 transition-all shadow-sm">
             Save
         </button>
         <button 
             onClick={() => setIsExportOpen(true)}
             className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 hover:text-slate-900 active:scale-95 text-xs font-bold uppercase tracking-widest rounded text-slate-700 transition-all shadow-sm"
         >
             Export
         </button>
         <button className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-xs font-black uppercase tracking-widest rounded text-white transition-all shadow-sm shadow-blue-600/20 border border-blue-700">
             Mark Reviewed
         </button>
      </div>

      {isExportOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center backdrop-blur-sm">
              <div className="bg-white border border-slate-200 w-[600px] shadow-2xl rounded p-6">
                  <div className="flex justify-between items-center mb-4 border-b border-slate-200 pb-2">
                      <h2 className="text-sm font-black uppercase text-slate-800 tracking-widest">Audit Export Payload</h2>
                      <button onClick={() => setIsExportOpen(false)} className="text-slate-500 hover:text-slate-900">✕</button>
                  </div>
                  <textarea 
                      readOnly
                      className="w-full h-96 bg-slate-50 border border-slate-200 rounded p-4 text-xs font-mono text-slate-800 resize-none outline-none custom-scrollbar"
                      value={exportText}
                  />
                  <div className="flex justify-end mt-4">
                      <button 
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 active:scale-95 text-xs font-black uppercase tracking-widest rounded text-white shadow transition-all duration-150"
                          onClick={() => {
                              navigator.clipboard.writeText(exportText);
                              setIsExportOpen(false);
                          }}
                      >
                          Copy to Clipboard
                      </button>
                  </div>
              </div>
          </div>
      )}
    </div>
  );
};
