"use client"

import { create } from "zustand"

interface ShellState {
  title: string
  setTitle: (title: string) => void
}

export const useShell = create<ShellState>((set) => ({
  title: "PrimoAuditAI",
  setTitle: (title) => set({ title }),
}))
