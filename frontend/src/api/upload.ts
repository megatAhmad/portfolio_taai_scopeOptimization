/**
 * Upload API functions
 */

import apiClient from './client';
import { UploadedData } from '@/store/types';

export const uploadAPI = {
  /**
   * Upload an Excel file
   */
  uploadFile: async (file: File): Promise<UploadedData> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post<UploadedData>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },
  
  /**
   * Get data preview with pagination
   */
  getPreview: async (
    sessionId: string,
    page: number = 1,
    pageSize: number = 50,
    sortBy?: string,
    sortOrder: 'asc' | 'desc' = 'asc'
  ) => {
    const response = await apiClient.get(`/upload/${sessionId}/preview`, {
      params: { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder },
    });
    
    return response.data;
  },
  
  /**
   * Get column statistics
   */
  getStats: async (sessionId: string) => {
    const response = await apiClient.get(`/upload/${sessionId}/stats`);
    return response.data;
  },
  
  /**
   * Get available sheets
   */
  getSheets: async (sessionId: string) => {
    const response = await apiClient.get(`/upload/${sessionId}/sheets`);
    return response.data;
  },
};
