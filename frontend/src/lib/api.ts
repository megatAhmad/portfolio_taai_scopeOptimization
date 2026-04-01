import type { ClassificationResult, ClassificationRowsPage, ClassificationRun, DatasetInspection, Project, ProjectDetail, RuleAst, RuleSet } from '../types'

const API_BASE = 'http://127.0.0.1:8000/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, options)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }
  return response.json()
}

export const api = {
  listProjects: () => request<Project[]>('/projects'),
  createProject: (payload: { name: string; description: string }) =>
    request<Project>('/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  getProjectDetail: (projectId: number) => request<ProjectDetail>('/projects/' + projectId),
  deleteProject: (projectId: number) => request<{ message: string }>('/projects/' + projectId, { method: 'DELETE' }),
  inspectDataset: (payload: FormData) =>
    request<DatasetInspection>('/datasets/inspect-file', {
      method: 'POST',
      body: payload,
    }),
  uploadDataset: (projectId: number, payload: FormData) =>
    request('/projects/' + projectId + '/datasets', {
      method: 'POST',
      body: payload,
    }),
  deleteDataset: (datasetId: number) => request<{ message: string }>('/datasets/' + datasetId, { method: 'DELETE' }),
  saveRuleSet: (projectId: number, payload: { name: string; ast_json: RuleAst }) =>
    request<RuleSet>('/projects/' + projectId + '/rulesets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  runClassification: (projectId: number) =>
    request<ClassificationResult>('/projects/' + projectId + '/classify', {
      method: 'POST',
    }),
  getClassificationRun: (runId: number) => request<ClassificationRun>('/classification-runs/' + runId),
  getClassificationRunRows: (runId: number, offset = 0, limit = 100) =>
    request<ClassificationRowsPage>('/classification-runs/' + runId + '/rows?offset=' + offset + '&limit=' + limit),
  exportClassificationRunUrl: (runId: number) => API_BASE + '/classification-runs/' + runId + '/export',
}

