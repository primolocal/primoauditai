import React from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, Upload, FileText, CheckCircle, RefreshCcw } from "lucide-react";

export default function GuidelinesAdminContent() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            {/* Admin Header */}
            <header className="bg-slate-900 text-white p-4 shadow-md flex justify-between items-center shrink-0 border-b border-indigo-500">
                <div className="flex items-center gap-4">
                    <Link href="/" className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-slate-800">
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div className="flex gap-2 items-center">
                        <BookOpen className="w-5 h-5 text-indigo-400" />
                        <h1 className="text-lg font-black tracking-tight flex items-baseline gap-2">
                            PrimoAudit Intelligence <span className="font-medium text-slate-400">| Guideline Management</span>
                        </h1>
                    </div>
                </div>
                <div className="flex gap-3">
                    <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded text-sm font-bold shadow-sm transition-colors">
                        <Upload className="w-4 h-4" />
                        Upload Guideline (PDF)
                    </button>
                </div>
            </header>
            
            <main className="flex-1 max-w-6xl w-full mx-auto p-6 flex flex-col gap-6">
                
                {/* Status Bar */}
                <div className="grid grid-cols-4 gap-4">
                    <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col">
                        <span className="text-slate-500 text-xs font-black uppercase tracking-widest mb-1">Active Carriers</span>
                        <span className="text-2xl font-light text-slate-800">12</span>
                    </div>
                    <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col">
                        <span className="text-indigo-500 text-xs font-black uppercase tracking-widest mb-1">Pending Syncs</span>
                        <span className="text-2xl font-light text-slate-800">2</span>
                    </div>
                    <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col">
                        <span className="text-emerald-500 text-xs font-black uppercase tracking-widest mb-1">Total Rules</span>
                        <span className="text-2xl font-light text-slate-800">1,402</span>
                    </div>
                    <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col">
                        <span className="text-purple-500 text-xs font-black uppercase tracking-widest mb-1">Intelligence Version</span>
                        <span className="text-2xl font-light text-slate-800">v2.1.0</span>
                    </div>
                </div>

                <div className="flex gap-6">
                    {/* Left List */}
                    <div className="w-1/3 flex flex-col gap-3">
                        <h2 className="text-xs font-black uppercase tracking-widest text-slate-500 mb-1">Carrier Profiles</h2>
                        
                        <div className="bg-white border-2 border-indigo-500 rounded p-4 cursor-pointer shadow-sm relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-1.5 h-full bg-indigo-500" />
                            <h3 className="font-bold text-slate-800 text-sm">National General</h3>
                            <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                                <CheckCircle className="w-3 h-3 text-emerald-500" /> Active: v2026_03
                            </div>
                        </div>

                        <div className="bg-white border border-slate-200 rounded p-4 cursor-pointer hover:border-slate-300 transition-colors">
                            <h3 className="font-bold text-slate-800 text-sm">State Farm</h3>
                            <div className="text-xs text-amber-600 mt-1 flex items-center gap-1 font-medium">
                                <RefreshCcw className="w-3 h-3" /> Update Pending (v2026_04)
                            </div>
                        </div>
                    </div>

                    {/* Right Pane (Detail) */}
                    <div className="flex-1 bg-white border border-slate-200 rounded-lg shadow-sm p-6 flex flex-col">
                        <div className="flex justify-between items-start border-b border-slate-200 pb-4 mb-4">
                            <div>
                                <h2 className="text-xl font-black text-slate-900">National General - v2026_03</h2>
                                <p className="text-sm text-slate-500 mt-1">Uploaded resolving 14 new rule drift conflicts via PrimoAudit Intelligence.</p>
                            </div>
                            <span className="bg-indigo-50 text-indigo-700 border border-indigo-200 px-3 py-1 rounded text-xs font-bold uppercase tracking-widest">
                                Active Production
                            </span>
                        </div>
                        
                        <h3 className="text-xs font-black uppercase tracking-widest text-slate-500 mb-3">Extracted Rules Registry (Sample)</h3>
                        
                        <div className="flex flex-col gap-2 overflow-y-auto">
                            <div className="flex gap-4 items-center p-3 border border-slate-100 bg-slate-50 rounded">
                                <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                                <div className="flex-1">
                                    <h4 className="text-xs font-bold text-slate-800">PHOTO_SUPPORT_REQUIRED</h4>
                                    <p className="text-xs text-slate-500 mt-0.5">Strictly mandate full panel replacements require both front and oblique angles.</p>
                                </div>
                                <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded border border-emerald-200">ACTIVE</span>
                            </div>
                            <div className="flex gap-4 items-center p-3 border border-indigo-100 bg-white rounded">
                                <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                                <div className="flex-1">
                                    <h4 className="text-xs font-bold text-slate-800">OEM_PARTS_SOURCING</h4>
                                    <p className="text-xs text-slate-500 mt-0.5">Current Carrier state allows A/M if LKQ is unavailable within 48 hours.</p>
                                </div>
                                <span className="text-[10px] font-bold px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded border border-indigo-200">AI GENERATED</span>
                            </div>
                        </div>
                    </div>
                </div>

            </main>
        </div>
    );
}
