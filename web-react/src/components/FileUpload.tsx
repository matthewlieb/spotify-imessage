import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, Music } from 'lucide-react';
import { FileUpload as FileUploadType } from '../types';

interface FileUploadProps {
  onFileSelect: (file: FileUploadType) => void;
  selectedFile?: FileUploadType | null;
  onRemoveFile: () => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFileSelect,
  selectedFile,
  onRemoveFile,
}) => {
  const [isDragActive, setIsDragActive] = useState(false);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        const fileUpload: FileUploadType = {
          file,
          name: file.name,
          size: file.size,
          type: file.type,
        };
        onFileSelect(fileUpload);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'text/csv': ['.csv'],
    },
    multiple: false,
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (selectedFile) {
    return (
      <div className="glass-card p-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-spotify-500/20 rounded-full">
              <FileText className="w-6 h-6 text-spotify-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white">{selectedFile.name}</h3>
              <p className="text-white/60 text-sm">{formatFileSize(selectedFile.size)}</p>
            </div>
          </div>
          <button
            onClick={onRemoveFile}
            className="p-2 hover:bg-white/10 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-white/60 hover:text-white" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`
        glass-card p-8 cursor-pointer transition-all duration-300
        ${isDragActive ? 'border-spotify-500 bg-spotify-500/10 scale-105' : 'border-white/20'}
        ${isDragReject ? 'border-red-500 bg-red-500/10' : ''}
        hover:border-spotify-500/50 hover:bg-spotify-500/5
      `}
    >
      <input {...getInputProps()} />
      <div className="text-center">
        <div className="mb-4">
          {isDragActive ? (
            <div className="animate-bounce-gentle">
              <Upload className="w-16 h-16 text-spotify-400 mx-auto" />
            </div>
          ) : (
            <div className="animate-pulse-gentle">
              <Music className="w-16 h-16 text-spotify-400 mx-auto" />
            </div>
          )}
        </div>
        
        <h3 className="text-xl font-semibold mb-2">
          {isDragActive ? 'Drop your file here' : 'Upload your message export'}
        </h3>
        
        <p className="text-white/60 mb-4">
          {isDragReject
            ? 'Invalid file type. Please upload a .txt or .csv file.'
            : 'Drag & drop your Android Messages export or click to browse'}
        </p>
        
        <div className="flex items-center justify-center space-x-2 text-sm text-white/40">
          <FileText className="w-4 h-4" />
          <span>Supports .txt and .csv files</span>
        </div>
      </div>
    </div>
  );
};
