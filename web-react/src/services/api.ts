import axios from 'axios';
import { ProcessingJob, ProcessingOptions, AppStats, UploadResponse } from '../types';

// Get API URL from environment or use smart defaults
const getApiBaseUrl = () => {
  // First try environment variable
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  
  // Fallback to localhost with common ports
  const ports = [8004, 8000, 5000, 3001];
  
  // Try to detect if backend is running on any of these ports
  for (const port of ports) {
    try {
      // This is a simple check - in production you'd want more sophisticated detection
      if (typeof window !== 'undefined') {
        // We're in the browser, use the current port
        return `http://localhost:${port}`;
      }
    } catch (e) {
      continue;
    }
  }
  
  // Default fallback
  return 'http://localhost:8004';
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export const uploadFile = async (
  file: File,
  options: ProcessingOptions
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  
  Object.entries(options).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      formData.append(key, String(value));
    }
  });

  const response = await api.post<UploadResponse>('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const getJobStatus = async (jobId: string): Promise<ProcessingJob> => {
  const response = await api.get<ProcessingJob>(`/status/${jobId}`);
  return response.data;
};

export const downloadResult = async (jobId: string): Promise<Blob> => {
  const response = await api.get(`/download/${jobId}`, {
    responseType: 'blob',
  });
  return response.data;
};

export const getStats = async (): Promise<AppStats> => {
  const response = await api.get<AppStats>('/api/stats');
  return response.data;
};

export const healthCheck = async (): Promise<{ status: string; timestamp: string }> => {
  const response = await api.get('/health');
  return response.data;
};
