"use client";
import React, { useState } from "react";
import { useAuditData } from "../AuditContext";

export const FileInventoryPanel: React.FC = () => {
    const { auditRun } = useAuditData();
    const [open, setOpen] = useState(false);

    if (!auditRun) return null;

    return (
        <div className="bg-white border border-slate-200 shadow-sm rounded-lg overflow-hidden">
            <div 
               className="text-[10px] font-black uppercase tracking-widest text-slate-700 p-3 flex justify-between items-center cursor-pointer bg-slate-50 hover:bg-slate-100 transition"
               onClick={() => setOpen(!open)}
            >
                <span>File Inventory ({auditRun.file_inventory.total_files})</span>
                <span>{open ? '▲' : '▼'}</span>
            </div>
            
            {open && (
                <div className="p-2 space-y-1 border-t border-slate-200 max-h-48 overflow-y-auto">
                    {auditRun.file_inventory.total_files === 0 ? (
                        <div className="italic text-slate-500 text-center p-6 border border-dashed border-slate-300 rounded bg-slate-50 text-xs">
                            No files in inventory
                        </div>
                    ) : (
                        <>
                    <div className="flex justify-between items-center p-1.5 hover:bg-slate-50 rounded cursor-pointer text-xs transition-colors">
                        <span className="text-slate-800 font-mono truncate max-w-[150px]">NATGEN-001.zip</span>
                        <span className="text-[9px] uppercase font-bold text-slate-500 border border-slate-200 bg-white shadow-sm px-1.5 py-0.5 rounded">EMS</span>
                    </div>
                    <div className="flex justify-between items-center p-1.5 hover:bg-slate-50 rounded cursor-pointer text-xs transition-colors">
                        <span className="text-slate-800 font-mono truncate max-w-[150px]">Est_Orig_PDF.pdf</span>
                        <span className="text-[9px] uppercase font-bold text-slate-500 border border-slate-200 bg-white shadow-sm px-1.5 py-0.5 rounded">PDF</span>
                    </div>
                    <div className="flex justify-between items-center p-1.5 hover:bg-slate-50 rounded cursor-pointer text-xs transition-colors">
                        <span className="text-slate-800 font-mono truncate max-w-[150px]">IMG_001_Front.jpg</span>
                        <span className="text-[9px] uppercase font-bold text-blue-700 border border-blue-200 bg-blue-50 px-1.5 py-0.5 rounded">JPG</span>
                    </div>
                        <div className="flex justify-between items-center p-1.5 hover:bg-slate-50 rounded cursor-pointer text-xs">
                            <span className="text-slate-500 italic text-[10px]">...17 more files</span>
                        </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};
