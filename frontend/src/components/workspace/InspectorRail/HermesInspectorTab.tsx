"use client";
import React from "react";
import { useAuditData } from "../AuditContext";

const ToneBadge = ({ tone }: { tone: string }) => {
    const config: Record<string, string> = {
        firm: 'bg-red-50 text-red-700 border-red-200',
        soft: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        cautionary: 'bg-amber-50 text-amber-700 border-amber-200',
        advisory: 'bg-blue-50 text-blue-700 border-blue-200',
    };
    return (
        <span className={`text-[9px] uppercase font-black tracking-widest px-1.5 py-0.5 rounded border ${config[tone] || config.advisory}`}>
            {tone}
        </span>
    );
};

const ConfBadge = ({ level }: { level: string }) => {
    const config: Record<string, string> = {
        high: 'bg-emerald-100 text-emerald-800',
        medium: 'bg-blue-100 text-blue-800',
        low: 'bg-slate-100 text-slate-600',
    };
    return (
        <span className={`text-[9px] uppercase font-black tracking-widest px-1.5 py-0.5 rounded ${config[level] || config.low}`}>
            {level} conf
        </span>
    );
};

export const HermesInspectorTab: React.FC = () => {
    const { auditRun, selectedFinding } = useAuditData();

    if (!auditRun) return <div className="text-xs text-slate-500 italic p-4">No audit data available.</div>;

    const showFinding = selectedFinding || auditRun.findings[0];
    if (!showFinding) return <div className="text-xs text-slate-500 italic p-4">No findings available.</div>;

    const f = showFinding;

    return (
        <div className="space-y-4">
            <div className="text-[10px] font-black uppercase tracking-widest text-indigo-500 mb-2 pb-1 border-b border-indigo-200">
                Hermes Intelligence
            </div>

            {/* Core AI Decision */}
            <div className={`border rounded p-3 shadow-sm ${
                f.hermes_recommended_action === 'approve' ? 'bg-emerald-50 border-emerald-200' :
                f.hermes_recommended_action === 'dismiss' ? 'bg-slate-50 border-slate-300' :
                'bg-amber-50 border-amber-200'
            }`}>
                <div className="flex items-center justify-between mb-2">
                    <span className="text-[9px] uppercase font-black tracking-widest text-slate-500">Hermes Recommendation</span>
                    <div className="flex items-center gap-2">
                        {f.advisory_tone && <ToneBadge tone={f.advisory_tone} />}
                        {f.hermes_confidence_level && <ConfBadge level={f.hermes_confidence_level} />}
                    </div>
                </div>

                <div className="text-sm font-black text-slate-900">
                    {f.hermes_recommended_action?.toUpperCase() || 'REVIEW'}
                </div>

                <div className="text-[11px] text-slate-700 font-medium mt-1 leading-snug">
                    {f.hermes_short_reason || f.message}
                </div>
            </div>

            {/* Full Rationale */}
            {f.hermes_rationale_summary && (
                <div className="bg-white border border-slate-200 rounded p-3 shadow-sm">
                    <div className="text-[9px] uppercase font-black tracking-widest text-slate-400 mb-1">Rationale</div>
                    <p className="text-[12px] text-slate-800 font-medium leading-relaxed">{f.hermes_rationale_summary}</p>
                </div>
            )}

            {/* Final Recommendation Text */}
            {f.final_recommendation_text && (
                <div className="bg-indigo-50 border border-indigo-200 rounded p-3 shadow-sm">
                    <div className="text-[9px] uppercase font-black tracking-widest text-indigo-400 mb-1">Full Advisory</div>
                    <p className="text-[11px] text-indigo-900 font-medium leading-relaxed italic">{f.final_recommendation_text}</p>
                </div>
            )}

            {/* Pattern Detection */}
            {f.pattern_detection_flags && f.pattern_detection_flags.length > 0 && (
                <div className="bg-purple-50 border border-purple-200 rounded p-3 shadow-sm">
                    <div className="text-[9px] uppercase font-black tracking-widest text-purple-400 mb-1">Pattern Detection</div>
                    <ul className="space-y-1">
                        {f.pattern_detection_flags.map((flag, i) => (
                            <li key={i} className="text-[11px] text-purple-800 font-medium flex items-start gap-1.5">
                                <span className="text-purple-400 mt-0.5">•</span>
                                {flag}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Action Playbook */}
            {f.action_playbook && (
                <div className="bg-white border border-slate-200 rounded p-3 shadow-sm">
                    <div className="text-[9px] uppercase font-black tracking-widest text-slate-400 mb-2">Action Playbook</div>
                    <div className="flex flex-col gap-3">
                        <div className="bg-slate-50 border border-slate-200 rounded p-2">
                            <div className="text-[9px] uppercase font-bold tracking-widest text-slate-500 mb-0.5">Primary Action</div>
                            <div className="text-[12px] font-black text-slate-900">{f.action_playbook.primary_action}</div>
                        </div>

                        {f.action_playbook.steps.length > 0 && (
                            <div>
                                <div className="text-[9px] uppercase font-bold tracking-widest text-slate-500 mb-1">Steps</div>
                                <ol className="list-decimal list-inside space-y-1">
                                    {f.action_playbook.steps.map((step, i) => (
                                        <li key={i} className="text-[11px] text-slate-700 font-medium leading-snug">{step}</li>
                                    ))}
                                </ol>
                            </div>
                        )}

                        {f.action_playbook.escalate_if.length > 0 && (
                            <div className="bg-amber-50 border border-amber-200 rounded p-2">
                                <div className="text-[9px] uppercase font-bold tracking-widest text-amber-600 mb-1">Escalate If</div>
                                <ul className="space-y-1">
                                    {f.action_playbook.escalate_if.map((cond, i) => (
                                        <li key={i} className="text-[10px] text-amber-800 font-bold">{cond}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {f.action_playbook.do_not_do.length > 0 && (
                            <div className="bg-red-50 border border-red-200 rounded p-2">
                                <div className="text-[9px] uppercase font-bold tracking-widest text-red-600 mb-1">Do Not</div>
                                <ul className="space-y-1">
                                    {f.action_playbook.do_not_do.map((item, i) => (
                                        <li key={i} className="text-[10px] text-red-800 font-bold">{item}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Guideline Citation */}
            {f.carrier_guideline_citation && (
                <div className="bg-slate-800 border border-slate-700 rounded p-3 shadow-sm">
                    <div className="text-[9px] uppercase font-black tracking-widest text-slate-300 mb-1">Guideline Citation</div>
                    <div className="text-[9px] text-slate-400 font-bold mb-1">
                        {f.carrier_guideline_citation.carrier} — {f.carrier_guideline_citation.version_label}
                    </div>
                    <div className="text-[10px] font-serif italic text-slate-100 leading-relaxed border-l-2 border-slate-600 pl-3">
                        "{f.carrier_guideline_citation.excerpt}"
                    </div>
                </div>
            )}

            {/* Claim-Level Banners */}
            {auditRun.advisory_banners && auditRun.advisory_banners.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-200 space-y-2">
                    <div className="text-[9px] uppercase font-black tracking-widest text-slate-400">Claim Banners</div>
                    {auditRun.advisory_banners.map((banner, i) => (
                        <div key={i} className={`border rounded p-2 ${
                            banner.type === 'warning' ? 'bg-amber-50 border-amber-200' :
                            banner.type === 'error' ? 'bg-red-50 border-red-200' :
                            banner.type === 'secondary' ? 'bg-blue-50 border-blue-200' :
                            'bg-slate-50 border-slate-200'
                        }`}>
                            <div className="text-[10px] font-black text-slate-800">{banner.title}</div>
                            <div className="text-[10px] text-slate-600 font-medium mt-0.5">{banner.message}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Metadata */}
            <div className="text-[9px] text-slate-400 font-mono pt-2 border-t border-slate-100">
                {f.hermes_version && <div>Version: {f.hermes_version}</div>}
                {f.template_family && <div>Template: {f.template_family}</div>}
                {f.strength_label && <div>Strength: {f.strength_label}</div>}
                {f.triage_bucket && <div>Bucket: {f.triage_bucket} (score: {f.triage_priority_score || 0})</div>}
            </div>
        </div>
    );
};
