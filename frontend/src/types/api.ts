export interface CleanupCandidateResponse {
  path: string
  risk: 'SAFE' | 'CAUTION' | 'DANGEROUS'
  ai_risk?: 'SAFE' | 'CAUTION' | 'DANGEROUS'  // AI-assessed risk (can be higher than scanner)
  effective_risk?: 'SAFE' | 'CAUTION' | 'DANGEROUS'  // Max of scanner and AI risk
  reason: string
  size_bytes: number
  size_human: string
}

export interface ScanResponse {
  project_path: string
  project_type: string
  framework: string
  package_manager: string
  language: string
  has_git: boolean
  git_clean: boolean
  cleanup_candidates: CleanupCandidateResponse[]
  total_recoverable_bytes: number
  total_recoverable_human: string
  protected_paths: string[]
  notes: string
}

export interface CleanupPlanItem {
  path: string
  action: 'DELETE' | 'KEEP'
  risk: 'SAFE' | 'CAUTION' | 'DANGEROUS'
  reason: string
  estimated_bytes: number
  regeneration_command?: string
}

export interface CleanupPlan {
  plan: CleanupPlanItem[]
  total_safe_recovery_bytes: number
  total_caution_recovery_bytes: number
  requires_approval: boolean
  warnings: string[]
  verification_steps: string[]
}

export interface RestoreOption {
  name: string
  description: string
  commands: string[]
  estimated_time_seconds: number
  risk: 'SAFE' | 'CAUTION' | 'DANGEROUS'
}

export interface RestoreGuidance {
  restore_options: RestoreOption[]
  prerequisites: string[]
  notes: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export interface ProjectManifest {
  project_name: string
  project_type: string
  framework: string
  language: string
  package_manager: string
  repository: string
  current_branch: string
  last_scan: string
  cleanup_history: CleanupHistoryEntry[]
  regenerated_artifacts: string[]
  important_commands: string[]
  restore_instructions: string[]
  project_health: 'HEALTHY' | 'DEGRADED' | 'BROKEN'
}

export interface CleanupHistoryEntry {
  date: string
  items_removed: string[]
  space_recovered: number
  verification_passed: boolean
}