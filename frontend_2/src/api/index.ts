import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export const getProjects = () => api.get("/projects/");
export const createProject = (data: { name: string }) => api.post("/projects/", data);
export const getProject = (id: number) => api.get(`/projects/${id}`);

export const uploadDataset = (projectId: number, formData: FormData) => 
  api.post(`/projects/${projectId}/datasets/`, formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });

export const getDatasets = (projectId: number) => api.get(`/projects/${projectId}/datasets/`);
export const getMapping = (projectId: number, datasetId: number) => api.get(`/projects/${projectId}/datasets/${datasetId}/mapping`);
export const createMapping = (projectId: number, datasetId: number, data: any) => api.post(`/projects/${projectId}/datasets/${datasetId}/mapping`, data);

export const getRuleSets = (projectId: number) => api.get(`/projects/${projectId}/rules/`);
export const createRuleSet = (projectId: number, data: any) => api.post(`/projects/${projectId}/rules/`, data);

export const runClassification = (projectId: number) => api.post(`/projects/${projectId}/classify/`);

export default api;
