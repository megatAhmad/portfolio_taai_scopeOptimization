/**
 * TypeScript types for the MWCS application
 */

// Session and Upload types
export interface ValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  detected_columns: string[];
  missing_required: string[];
  missing_optional: string[];
}

export interface UploadedData {
  session_id: string;
  filename: string;
  total_rows: number;
  columns: string[];
  validation: ValidationResult;
  preview: Record<string, any>[];
  sheet_names: string[];
}

// Rule types
export type RuleType = 'numeric' | 'text' | 'date' | 'lookup' | 'aggregation' | 'conditional' | 'business';
export type DecisionOutcome = 'ACCEPTED' | 'RECONSIDER' | 'REJECTED';

export interface RuleCondition {
  field: string;
  rule_type: RuleType;
  operator: string;
  value: any;
  value_end?: any;
  lookup_dataset?: string;
  lookup_field?: string;
}

export interface Rule {
  rule_id: string;
  name: string;
  description?: string;
  rule_type: string;
  priority: number;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

// Processing types
export interface AIConfig {
  provider: 'azure' | 'openrouter';
  model: string;
  api_key?: string;
  endpoint?: string;
  temperature: number;
  max_tokens: number;
}

export interface ProcessingStatus {
  session_id: string;
  status: 'idle' | 'processing' | 'completed' | 'error';
  progress: number;
  current_row?: number;
  total_rows?: number;
  message?: string;
  error?: string;
}

export interface ProcessingSummary {
  session_id: string;
  total_processed: number;
  accepted_count: number;
  reconsider_count: number;
  rejected_count: number;
  processing_time_seconds: number;
  rules_applied: number;
  justifications_generated: number;
  summary_stats: Record<string, any>;
}

// Application state
export interface AppState {
  // Session
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  
  // Upload
  uploadedData: UploadedData | null;
  setUploadedData: (data: UploadedData | null) => void;
  
  // Rules
  rules: Rule[];
  setRules: (rules: Rule[]) => void;
  addRule: (rule: Rule) => void;
  updateRule: (ruleId: string, updates: Partial<Rule>) => void;
  deleteRule: (ruleId: string) => void;
  
  // Processing
  processingStatus: ProcessingStatus | null;
  setProcessingStatus: (status: ProcessingStatus | null) => void;
  
  processingSummary: ProcessingSummary | null;
  setProcessingSummary: (summary: ProcessingSummary | null) => void;
  
  // AI Config
  aiConfig: AIConfig | null;
  setAIConfig: (config: AIConfig | null) => void;
  
  // Navigation
  currentStep: number;
  setCurrentStep: (step: number) => void;
  
  // Reset
  reset: () => void;
}
