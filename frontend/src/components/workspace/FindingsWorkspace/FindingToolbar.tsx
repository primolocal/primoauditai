"use client";
import React from "react";

interface FindingToolbarProps {
    searchQuery: string;
    onSearchChange: (q: string) => void;
    sortBy: string;
    onSortChange: (sort: string) => void;
    statusFilter: string | null;
    onStatusFilterChange: (status: string | null) => void;
    severityFilter: string | null;
    onSeverityFilterChange: (severity: string | null) => void;
    totalCount: number;
    openCount: number;
}

export const FindingToolbar: React.FC<FindingToolbarProps> = ({
    searchQuery,
    onSearchChange,
    sortBy,
    onSortChange,
    statusFilter,
    onStatusFilterChange,
    severityFilter,
    onSeverityFilterChange,
    totalCount,
    openCount,
}) => {
    return (
        <div className="flex flex-col gap-3 pb-4 border-b border-slate-200">
            <div className="flex justify-between items-center">
                <input
                    type="text"
                    placeholder="Search findings (e.g. L8, OEM)..."
                    value={searchQuery}
                    onChange={(e) => onSearchChange(e.target.value)}
                    className="bg-white border border-slate-300 rounded px-3 py-1.5 text-xs text-slate-800 w-64 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 transition shadow-sm"
                />

                <div className="flex items-center gap-2">
                    <span className="text-[9px] uppercase font-black text-slate-500 tracking-widest">Sort:</span>
                    <select
                        value={sortBy}
                        onChange={(e) => onSortChange(e.target.value)}
                        className="bg-white border border-slate-300 text-slate-800 text-xs rounded px-2 py-1 outline-none shadow-sm"
                    >
                        <option value="severity">Severity (High → Low)</option>
                        <option value="line_number">Line Number</option>
                        <option value="confidence">Confidence</option>
                        <option value="financial_impact">Financial Impact</option>
                    </select>
                </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
                <span className="text-[9px] uppercase font-black text-slate-500 tracking-widest mr-2">Filters:</span>

                {/* Status: All */}
                <button
                    onClick={() => onStatusFilterChange(null)}
                    className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${
                        !statusFilter
                            ? "border-blue-200 bg-blue-50 text-blue-700"
                            : "border-slate-300 bg-white hover:bg-slate-50 text-slate-600"
                    }`}
                >
                    All ({totalCount})
                </button>

                {/* Status: Open Only */}
                <button
                    onClick={() => onStatusFilterChange(statusFilter === "open" ? null : "open")}
                    className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${
                        statusFilter === "open"
                            ? "border-blue-200 bg-blue-50 text-blue-700"
                            : "border-slate-300 bg-white hover:bg-slate-50 text-slate-600"
                    }`}
                >
                    Open Only ({openCount})
                </button>

                <div className="w-px h-3 bg-slate-300 mx-2"></div>

                {/* Severity: Critical */}
                <button
                    onClick={() => onSeverityFilterChange(severityFilter === "critical" ? null : "critical")}
                    className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${
                        severityFilter === "critical"
                            ? "border-red-200 bg-red-50 text-red-700"
                            : "border-slate-300 bg-white hover:border-red-200 hover:bg-red-50 hover:text-red-700 text-slate-600"
                    }`}
                >
                    Critical
                </button>

                {/* Severity: Major */}
                <button
                    onClick={() => onSeverityFilterChange(severityFilter === "major" ? null : "major")}
                    className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${
                        severityFilter === "major"
                            ? "border-amber-200 bg-amber-50 text-amber-700"
                            : "border-slate-300 bg-white hover:border-amber-200 hover:bg-amber-50 hover:text-amber-700 text-slate-600"
                    }`}
                >
                    Major
                </button>

                {/* Severity: Minor */}
                <button
                    onClick={() => onSeverityFilterChange(severityFilter === "minor" ? null : "minor")}
                    className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border shadow-sm transition-colors ${
                        severityFilter === "minor"
                            ? "border-slate-400 bg-slate-100 text-slate-700"
                            : "border-slate-300 bg-white hover:bg-slate-50 text-slate-600"
                    }`}
                >
                    Minor
                </button>
            </div>
        </div>
    );
};
