import React from "react";
import Link from "next/link";
import { ArrowLeft, BrainCircuit, Activity, Check, X, ThumbsUp, ThumbsDown } from "lucide-react";

export default function LearningAdminContent() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <header className="bg-slate-900 text-white p-4 shadow-md flex justify-between items-center shrink-0 border-b border-indigo-500">
                <div className="flex items-center gap-4">
                    <Link href="/" className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-slate-800">
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div className="flex gap-2 items-center">
                        <BrainCircuit className="w-5 h-5 text-indigo-400" />
                        <h1 className="text-lg font-black tracking-tight flex items-baseline gap-2">
                            PrimoAudit Intelligence <span className="font-medium text-slate-400">| Intelligence & Learning Metrics</span>
                        </h1>
                    </div>
                </div>
                <div className="flex gap-4 text-xs font-bold items-center">
                    <span className="text-emerald-400 flex items-center gap-1">
                        <Activity className="w-4 h-4" /> Live Sync Active
                    </span>
                    <button className="bg-white text-slate-900 px-4 py-2 rounded shadow-sm hover:bg-slate-200 transition-colors uppercase tracking-widest">
                        Generate Weekly Digest
                    </button>
                </div>
            </header>

            <main className="flex-1 max-w-6xl w-full mx-auto p-6 flex flex-col gap-6">
                
                {/* Aggregate Stats */}
                <div className="flex items-center gap-6 p-6 bg-white border border-slate-200 rounded-lg shadow-sm">
                    <div className="flex flex-col border-r border-slate-200 pr-6">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1">Human Overrides Trailed</span>
                        <span className="text-4xl font-light text-slate-800">4,129</span>
                    </div>
                    <div className="flex flex-col border-r border-slate-200 pr-6 pl-6">
                        <span className="text-[10px] font-black uppercase text-emerald-500 tracking-widest mb-1">Critiques Accepted</span>
                        <span className="text-4xl font-light text-slate-800">82%</span>
                    </div>
                    <div className="flex flex-col pl-6">
                        <span className="text-[10px] font-black uppercase text-indigo-500 tracking-widest mb-1">Pending Rule Adoptions</span>
                        <span className="text-4xl font-light text-slate-800">14</span>
                    </div>
                </div>

                {/* Training Recommendations List */}
                <div className="flex flex-col gap-4">
                    <h2 className="text-sm font-black uppercase tracking-widest text-slate-500 border-b border-slate-200 pb-2">
                        Suggested Rule Adjustments (Requires Human Review)
                    </h2>

                    <div className="bg-white border-2 border-amber-400 rounded-lg p-5 shadow-sm relative overflow-hidden flex flex-col gap-3">
                        <div className="absolute top-0 right-0 w-2 h-full bg-amber-400" />
                        
                        <div className="flex justify-between items-start">
                            <div>
                                <span className="bg-indigo-50 border border-indigo-200 text-indigo-700 text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded">High Confidence Pattern</span>
                                <h3 className="text-lg font-black text-slate-800 mt-2">Deduct 2pts for Missing R&I Bracket over Standard Labor</h3>
                                <p className="text-sm text-slate-500 max-w-prose mt-1">
                                    Auditors have dismissed the R_AND_I rule 47 times this week solely when replacing adjacent brackets. PrimoAudit Intelligence recommends mutating rule target to exclude inner-brackets.
                                </p>
                            </div>
                            <div className="flex gap-2">
                                <button className="bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 px-3 py-1.5 rounded flex items-center gap-1 text-[10px] font-black uppercase tracking-widest shadow-sm transition-colors">
                                    <Check className="w-4 h-4" /> Approve Evolution
                                </button>
                                <button className="bg-white text-slate-500 hover:text-red-600 hover:bg-red-50 border border-slate-200 px-3 py-1.5 rounded flex items-center gap-1 text-[10px] font-black uppercase tracking-widest shadow-sm transition-colors">
                                    <X className="w-4 h-4" /> Reject
                                </button>
                            </div>
                        </div>

                        <div className="bg-slate-50 border border-slate-200 rounded p-3 text-xs mt-2 relative grid grid-cols-2 gap-4">
                           <div>
                                <h4 className="font-bold text-slate-700 mb-1 border-b border-slate-200 pb-1">Current Behavior</h4>
                                <code className="block p-2 bg-slate-800 text-slate-300 rounded overflow-x-auto text-[10px]">
                                    if op == "R_AND_I" and hours {'>'} 0:<br/>
                                    &nbsp;&nbsp;flag_overlap()
                                </code>
                           </div>
                           <div>
                                <h4 className="font-bold text-emerald-700 mb-1 border-b border-emerald-200 pb-1">Proposed Optimization</h4>
                                <code className="block p-2 bg-emerald-950 text-emerald-300 rounded overflow-x-auto text-[10px]">
                                    if op == "R_AND_I" and hours {'>'} 0:<br/>
                                    &nbsp;&nbsp;if "bracket" not in desc.lower():<br/>
                                    &nbsp;&nbsp;&nbsp;&nbsp;flag_overlap()
                                </code>
                           </div>
                        </div>
                    </div>

                    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm flex flex-col gap-2 opacity-75">
                         <div className="flex justify-between items-start">
                            <div>
                                <span className="bg-slate-100 border border-slate-200 text-slate-500 text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded">Learning Observation</span>
                                <h3 className="text-lg font-black text-slate-800 mt-2">Differentiate OEM markup limits per-carrier</h3>
                                <p className="text-sm text-slate-500 max-w-prose mt-1">
                                    Auditors are modifying the OEM_MARKUP severity down to 'Minor' instead of overriding. Carrier 'Liberty' typically permits this up to 30%.
                                </p>
                            </div>
                            <div className="flex gap-2">
                                <button className="bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 px-3 py-1.5 rounded flex items-center gap-1 text-[10px] font-black uppercase tracking-widest shadow-sm transition-colors">
                                    <ThumbsUp className="w-3 h-3" /> Start Research
                                </button>
                                <button className="bg-white text-slate-500 hover:bg-slate-100 border border-slate-200 px-3 py-1.5 rounded flex items-center gap-1 text-[10px] font-black uppercase tracking-widest shadow-sm transition-colors">
                                    <ThumbsDown className="w-3 h-3" /> Ignore
                                </button>
                            </div>
                        </div>
                    </div>

                </div>

            </main>
        </div>
    );
}
