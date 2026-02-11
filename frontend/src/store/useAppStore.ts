/**
 * Zustand store for MWCS application state
 */

import { create } from 'zustand';
import { AppState } from './types';

export const useAppStore = create<AppState>((set) => ({
  // Session
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),
  
  // Upload
  uploadedData: null,
  setUploadedData: (data) => set({ uploadedData: data }),
  
  // Rules
  rules: [],
  setRules: (rules) => set({ rules }),
  addRule: (rule) => set((state) => ({ rules: [...state.rules, rule] })),
  updateRule: (ruleId, updates) => set((state) => ({
    rules: state.rules.map((rule) =>
      rule.rule_id === ruleId ? { ...rule, ...updates } : rule
    ),
  })),
  deleteRule: (ruleId) => set((state) => ({
    rules: state.rules.filter((rule) => rule.rule_id !== ruleId),
  })),
  
  // Processing
  processingStatus: null,
  setProcessingStatus: (status) => set({ processingStatus: status }),
  
  processingSummary: null,
  setProcessingSummary: (summary) => set({ processingSummary: summary }),
  
  // AI Config
  aiConfig: null,
  setAIConfig: (config) => set({ aiConfig: config }),
  
  // Navigation
  currentStep: 0,
  setCurrentStep: (step) => set({ currentStep: step }),
  
  // Reset
  reset: () => set({
    sessionId: null,
    uploadedData: null,
    rules: [],
    processingStatus: null,
    processingSummary: null,
    aiConfig: null,
    currentStep: 0,
  }),
}));
