"use client";

import React, { useState, useEffect } from "react";
import { Users, TrendingUp, Lightbulb, AlertTriangle, Crosshair, ArrowRight, ShieldCheck, Zap } from "lucide-react";

interface CarrierDifficulty {
    carrier: string;
    difficulty_flag: string;
}

interface CoachingProfile {
    auditor_id: string;
    strengths: string[];
    coaching_opportunities: string[];
    carrier_breakdown: CarrierDifficulty[];
    sample_size: number;
}

export default function CoachingDashboardContent() {
    const [auditors, setAuditors] = useState<string[]>([]);
    const [selectedAuditor, setSelectedAuditor] = useState<string | null>(null);
    const [profile, setProfile] = useState<CoachingProfile | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetch("/api/learning/coaching/auditors")
            .then(res => res.json())
            .then(data => {
                const list = data.auditors || [];
                setAuditors(list);
                if (list.length > 0 && !selectedAuditor) {
                    setSelectedAuditor(list[0]);
                }
            })
            .catch(err => console.error("Failed to load auditors", err));
    }, []);

    useEffect(() => {
        if (!selectedAuditor) return;
        setLoading(true);
        fetch(`/api/learning/coaching/auditor/${encodeURIComponent(selectedAuditor)}`)
            .then(res => res.json())
            .then(data => {
                setProfile(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load profile", err);
                setLoading(false);
            });
    }, [selectedAuditor]);

    const getDifficultyColor = (flag: string) => {
        switch (flag) {
            case "Extreme Difficulty": return "bg-rose-100 text-rose-800 border-rose-300";
            case "Elevated Friction": return "bg-amber-100 text-amber-800 border-amber-300";
            case "High Adherence": return "bg-emerald-100 text-emerald-800 border-emerald-300";
            default: return "bg-slate-100 text-slate-600 border-slate-200";
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 p-6 md:p-10 font-sans text-slate-900">
            <div className="max-w-6xl mx-auto space-y-6">
                
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-black text-slate-800 tracking-tight flex items-center gap-3">
                            <Users className="w-7 h-7 text-indigo-500" />
                            Auditor Coaching Visibility
                        </h1>
                        <p className="text-sm text-slate-500 mt-1 font-medium">
                            Qualitative performance patterns and actionable advisory coaching (Phase 20A)
                        </p>
                    </div>
                </div>

                <div className="flex flex-col lg:flex-row gap-6 items-start mt-6">
                    <div className="w-full lg:w-1/4 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                        <div className="bg-slate-100 px-4 py-3 border-b border-slate-200">
                            <h2 className="text-xs font-black uppercase tracking-widest text-slate-500 flex items-center gap-2">
                                <Crosshair className="w-4 h-4" /> Team Roster
                            </h2>
                        </div>
                        <div className="flex flex-col max-h-[600px] overflow-y-auto p-2">
                            {auditors.map((auditor) => (
                                <button
                                    key={auditor}
                                    onClick={() => setSelectedAuditor(auditor)}
                                    className={`text-left px-4 py-3 rounded-lg text-sm font-semibold transition-all mb-1 ${
                                        selectedAuditor === auditor 
                                        ? "bg-indigo-50 text-indigo-700 shadow-sm border border-indigo-100" 
                                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-800 border border-transparent"
                                    }`}
                                >
                                    {auditor}
                                </button>
                            ))}
                            {auditors.length === 0 && (
                                <div className="p-4 text-xs text-slate-400 italic text-center">No auditors found.</div>
                            )}
                        </div>
                    </div>

                    <div className="w-full lg:w-3/4 flex flex-col gap-6">
                        {loading && (
                            <div className="bg-white rounded-xl p-12 shadow-sm border border-slate-200 flex items-center justify-center animate-pulse">
                                <div className="text-slate-400 font-medium">Synthesizing telemetry...</div>
                            </div>
                        )}

                        {!loading && profile && (
                            <>
                                <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 flex justify-between items-center">
                                    <div>
                                        <h2 className="text-xl font-black text-slate-800">{profile.auditor_id}</h2>
                                        <p className="text-xs text-slate-400 uppercase tracking-widest mt-1 font-bold">
                                            {profile.sample_size} Scoped Decisions Modeled
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2 bg-indigo-50 text-indigo-700 px-3 py-1.5 rounded-full text-xs font-bold border border-indigo-100">
                                        <ShieldCheck className="w-4 h-4" /> Non-Punitive Mode
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="bg-emerald-50 rounded-xl p-6 shadow-sm border border-emerald-100 flex flex-col h-full">
                                        <h3 className="text-xs font-black uppercase tracking-widest text-emerald-800 flex items-center gap-2 mb-4">
                                            <Zap className="w-4 h-4" /> Validated Strengths
                                        </h3>
                                        <div className="flex flex-col gap-3 flex-grow">
                                            {profile.strengths.length > 0 ? profile.strengths.map((str, i) => (
                                                <div key={i} className="bg-white/60 p-3 rounded-lg text-sm text-emerald-900 border border-emerald-200 shadow-sm flex items-start gap-3 leading-relaxed">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 shrink-0"></div>
                                                    <span>{str}</span>
                                                </div>
                                            )) : (
                                                <div className="text-sm text-emerald-600/60 italic p-2 border border-dashed border-emerald-200 rounded-lg text-center">
                                                    Monitoring telemetry...
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="bg-amber-50 rounded-xl p-6 shadow-sm border border-amber-100 flex flex-col h-full">
                                        <h3 className="text-xs font-black uppercase tracking-widest text-amber-800 flex items-center gap-2 mb-4">
                                            <Lightbulb className="w-4 h-4" /> Coaching Opportunities
                                        </h3>
                                        <div className="flex flex-col gap-3 flex-grow">
                                            {profile.coaching_opportunities.length > 0 ? profile.coaching_opportunities.map((opp, i) => (
                                                <div key={i} className="bg-white/60 p-3 rounded-lg text-sm text-amber-900 border border-amber-200 shadow-sm flex items-start gap-3 leading-relaxed">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-2 shrink-0"></div>
                                                    <span>{opp}</span>
                                                </div>
                                            )) : (
                                                <div className="text-sm text-amber-600/60 italic p-2 border border-dashed border-amber-200 rounded-lg text-center">
                                                    No divergent actions detected.
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {profile.carrier_breakdown.length > 0 && (
                                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                                        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200">
                                            <h3 className="text-xs font-black uppercase tracking-widest text-slate-500 flex items-center gap-2">
                                                <AlertTriangle className="w-4 h-4" /> Localized Carrier Friction
                                            </h3>
                                        </div>
                                        <div className="p-6">
                                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                                {profile.carrier_breakdown.map((carr, i) => (
                                                    <div key={i} className={`p-4 rounded-xl border flex flex-col gap-2 ${getDifficultyColor(carr.difficulty_flag)}`}>
                                                        <span className="text-[10px] font-black uppercase tracking-widest opacity-60">
                                                            {carr.carrier}
                                                        </span>
                                                        <span className="font-bold text-sm tracking-tight leading-snug">
                                                            {carr.difficulty_flag}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}
                                
                            </>
                        )}
                        
                    </div>
                </div>
            </div>
        </div>
    );
}
