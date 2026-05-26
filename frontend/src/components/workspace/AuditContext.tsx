"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from "react";
import { AuditRun, Finding } from "@/types/claim";
import { AuditorVerdict } from "./InspectorRail/SupportVerdictBar";
import { apiUrl } from "@/lib/api";

export type SyncState = 'idle' | 'saving' | 'saved' | 'error';

export interface PhotoConfirmationState {
    evidence_exists?: 'yes'|'no'|'unknown'|null;
    evidence_uploaded?: 'yes'|'no'|null;
    linked_asset_ids?: string[];
    missing_upload_reason?: string|null;
}

// ─── Context 1: AuditDataContext (stable data, rarely changes) ───
interface AuditDataContextType {
  auditRun: AuditRun | null;
  setAuditRun: (run: AuditRun | null) => void;
  selectedFinding: Finding | null;
}

const AuditDataContext = createContext<AuditDataContextType | undefined>(undefined);

export const useAuditData = () => {
  const ctx = useContext(AuditDataContext);
  if (ctx === undefined) throw new Error("useAuditData must be used within an AuditProvider");
  return ctx;
};

// ─── Context 2: AuditInteractionContext (changes frequently, small scope) ───
interface AuditInteractionContextType {
  selectedFindingId: string | null;
  setSelectedFindingId: (id: string | null) => void;
  activeInspectorTab: string;
  setActiveInspectorTab: (tab: string) => void;
  verdictStore: Record<string, AuditorVerdict>;
  setVerdictStore: React.Dispatch<React.SetStateAction<Record<string, AuditorVerdict>>>;
  reviewerNotes: Record<string, string>;
  setReviewerNotes: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  photoConfirmations: Record<string, PhotoConfirmationState>;
  setPhotoConfirmations: React.Dispatch<React.SetStateAction<Record<string, PhotoConfirmationState>>>;
  saveAssetVerdict: (stateKey: string, verdict: AuditorVerdict) => Promise<void>;
  saveReviewerNote: (findingId: string, note: string) => Promise<void>;
  savePhotoConfirmation: (findingId: string, payload: Partial<PhotoConfirmationState>) => Promise<void>;
}

const AuditInteractionContext = createContext<AuditInteractionContextType | undefined>(undefined);

export const useAuditInteraction = () => {
  const ctx = useContext(AuditInteractionContext);
  if (ctx === undefined) throw new Error("useAuditInteraction must be used within an AuditProvider");
  return ctx;
};

// ─── Context 3: SyncContext (separate concern) ───
interface SyncContextType {
  syncState: SyncState;
  lastSavedAt: Date | null;
  unsyncedCount: number;
  retrySync: () => Promise<void>;
}

const SyncContext = createContext<SyncContextType | undefined>(undefined);

export const useSync = () => {
  const ctx = useContext(SyncContext);
  if (ctx === undefined) throw new Error("useSync must be used within an AuditProvider");
  return ctx;
};

// ─── Unified provider that wraps all 3 contexts ───
export const AuditProvider: React.FC<{ children: React.ReactNode; initialRun?: AuditRun }> = ({ 
  children, 
  initialRun = null 
}) => {
  // ── Data state ──
  const [auditRun, setAuditRun] = useState<AuditRun | null>(initialRun);

  // ── Interaction state ──
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [activeInspectorTab, setActiveInspectorTab] = useState<string>("estimate_detail");
  const [verdictStore, setVerdictStore] = useState<Record<string, AuditorVerdict>>({});
  const [reviewerNotes, setReviewerNotes] = useState<Record<string, string>>({});
  const [photoConfirmations, setPhotoConfirmations] = useState<Record<string, PhotoConfirmationState>>({});

  // ── Sync state ──
  const [syncState, setSyncState] = useState<SyncState>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [unsyncedCount, setUnsyncedCount] = useState(0);

  const failedQueue = useRef(new Map<string, () => Promise<void>>());
  const isRetrying = useRef(false);
  const decayTimerRef = useRef<NodeJS.Timeout | null>(null);

  // ── Derived ──
  const selectedFinding = useMemo(
    () => auditRun?.findings.find(f => f.id === selectedFindingId) || null,
    [auditRun?.findings, selectedFindingId]
  );

  // ── Sync helpers ──
  const setSavedWithDecay = useCallback(() => {
    setSyncState('saved');
    setLastSavedAt(new Date());
    if (decayTimerRef.current) clearTimeout(decayTimerRef.current);
    decayTimerRef.current = setTimeout(() => {
        setSyncState(prev => prev === 'saved' ? 'idle' : prev);
    }, 3000);
  }, []);

  const handleSyncAttempt = useCallback(async (targetKey: string, apiCall: () => Promise<void>) => {
    setSyncState('saving');
    try {
      await apiCall();
      failedQueue.current.delete(targetKey);
      setUnsyncedCount(failedQueue.current.size);
      if (failedQueue.current.size === 0) {
          setSavedWithDecay();
      }
    } catch (err) {
      failedQueue.current.set(targetKey, apiCall);
      setUnsyncedCount(failedQueue.current.size);
      setSyncState('error');
    }
  }, [setSavedWithDecay]);

  // ── Hydrate review state on auditRun change ──
  useEffect(() => {
    if (!auditRun) return;
    const fetchState = async () => {
      try {
        const res = await fetch(apiUrl(`/api/audit/${auditRun.run_id}/review-state`));
        if (res.ok) {
          const data = await res.json();
          setVerdictStore(data.asset_verdicts || {});
          setReviewerNotes(data.reviewer_notes || {});
          setPhotoConfirmations(data.finding_confirmations || {});
          setSavedWithDecay();
        }
      } catch (err) {
        console.error("Failed to hydrate review state", err);
        setSyncState('error');
      }
    };
    fetchState();
  }, [auditRun, setSavedWithDecay]);

  // ── Retry sync ──
  const retrySync = useCallback(async () => {
    if (failedQueue.current.size === 0 || isRetrying.current) return;
    isRetrying.current = true;
    setSyncState('saving');
    
    const tasks = Array.from(failedQueue.current.entries());
    let hasError = false;
    
    for (const [key, task] of tasks) {
        try {
            await task();
            failedQueue.current.delete(key);
        } catch(e) {
            hasError = true;
        }
    }
    
    setUnsyncedCount(failedQueue.current.size);
    if (hasError) {
        setSyncState('error');
    } else {
        setSavedWithDecay();
    }
    isRetrying.current = false;
  }, [setSavedWithDecay]);

  // ── Save functions ──
  const saveAssetVerdict = useCallback(async (stateKey: string, verdict: AuditorVerdict) => {
    if (!auditRun) return;
    const updatedVerdict = verdict === verdictStore[stateKey] ? null : verdict;
    setVerdictStore(prev => ({ ...prev, [stateKey]: updatedVerdict }));
    
    const targetKey = `asset-verdict:${auditRun.run_id}:${stateKey}`;
    await handleSyncAttempt(targetKey, async () => {
      const resp = await fetch(apiUrl(`/api/audit/${auditRun.run_id}/asset-verdict`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state_key: stateKey, verdict: updatedVerdict })
      });
      if (!resp.ok) throw new Error("Sync failure");
    });
  }, [auditRun, verdictStore, handleSyncAttempt]);

  const saveReviewerNote = useCallback(async (findingId: string, note: string) => {
    if (!auditRun) return;
    
    const targetKey = `finding-review:${auditRun.run_id}:${findingId}`;
    await handleSyncAttempt(targetKey, async () => {
      const resp = await fetch(apiUrl(`/api/audit/${auditRun.run_id}/finding-review`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ finding_id: findingId, note })
      });
      if (!resp.ok) throw new Error("Sync failure");
    });
  }, [auditRun, handleSyncAttempt]);

  const savePhotoConfirmation = useCallback(async (findingId: string, payload: Partial<PhotoConfirmationState>) => {
    if (!auditRun) return;

    setPhotoConfirmations(prev => {
        const existing = prev[findingId] || {};
        return { ...prev, [findingId]: { ...existing, ...payload } };
    });

    const targetKey = `photo-confirmation:${auditRun.run_id}:${findingId}`;
    await handleSyncAttempt(targetKey, async () => {
      const resp = await fetch(apiUrl(`/api/audit/${auditRun.run_id}/finding-review`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ finding_id: findingId, ...payload })
      });
      if (!resp.ok) throw new Error("Sync failure");
    });
  }, [auditRun, handleSyncAttempt]);

  // ── Memoize each context value to prevent unnecessary re-renders ──
  const dataValue = useMemo(() => ({
    auditRun,
    setAuditRun,
    selectedFinding,
  }), [auditRun, selectedFinding]);

  const interactionValue = useMemo(() => ({
    selectedFindingId,
    setSelectedFindingId,
    activeInspectorTab,
    setActiveInspectorTab,
    verdictStore,
    setVerdictStore,
    reviewerNotes,
    setReviewerNotes,
    photoConfirmations,
    setPhotoConfirmations,
    saveAssetVerdict,
    saveReviewerNote,
    savePhotoConfirmation,
  }), [
    selectedFindingId,
    activeInspectorTab,
    verdictStore,
    reviewerNotes,
    photoConfirmations,
    saveAssetVerdict,
    saveReviewerNote,
    savePhotoConfirmation,
  ]);

  const syncValue = useMemo(() => ({
    syncState,
    lastSavedAt,
    unsyncedCount,
    retrySync,
  }), [syncState, lastSavedAt, unsyncedCount, retrySync]);

  return (
    <AuditDataContext.Provider value={dataValue}>
      <AuditInteractionContext.Provider value={interactionValue}>
        <SyncContext.Provider value={syncValue}>
          {children}
        </SyncContext.Provider>
      </AuditInteractionContext.Provider>
    </AuditDataContext.Provider>
  );
};

// ─── Backward-compatible unified hook ───
export const useAudit = () => {
  const data = useAuditData();
  const interaction = useAuditInteraction();
  const sync = useSync();
  return { ...data, ...interaction, ...sync };
};
