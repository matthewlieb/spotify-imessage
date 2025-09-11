export interface ProcessingJob {
  job_id: string;
  status: 'processing' | 'completed' | 'error';
  progress: number;
  message: string;
  file: string;
  output?: string;
}

export interface ProcessingOptions {
  command_type: 'android' | 'file';
  playlist_id?: string;
  start_date?: string;
  end_date?: string;
  days_back?: number;
  show_metadata: boolean;
  dry_run: boolean;
  stats: boolean;
}

export interface AppStats {
  total_jobs: number;
  completed_jobs: number;
  error_jobs: number;
  processing_jobs: number;
  uptime: string;
}

export interface UploadResponse {
  job_id: string;
  message: string;
}

export interface FileUpload {
  file: File;
  name: string;
  size: number;
  type: string;
}
