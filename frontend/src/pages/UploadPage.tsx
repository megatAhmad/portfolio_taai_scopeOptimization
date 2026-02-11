/**
 * Upload Page - Step 1
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAppStore } from '@/store/useAppStore';
import { uploadAPI } from '@/api/upload';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setUploadedData = useAppStore((state) => state.setUploadedData);
  const setSessionId = useAppStore((state) => state.setSessionId);
  const setCurrentStep = useAppStore((state) => state.setCurrentStep);
  
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setIsUploading(true);
    setError(null);
    
    try {
      const data = await uploadAPI.uploadFile(file);
      setUploadedData(data);
      setSessionId(data.session_id);
      setCurrentStep(1);
      navigate('/rules');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };
  
  return (
    <div className="max-w-2xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Upload Data File</CardTitle>
          <CardDescription>
            Upload an Excel file containing maintenance work data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* File upload area */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-gray-400 transition-colors">
              <Upload className="mx-auto h-12 w-12 text-gray-400" />
              <div className="mt-4">
                <label htmlFor="file-upload" className="cursor-pointer">
                  <span className="text-blue-600 hover:text-blue-500 font-medium">
                    Choose a file
                  </span>
                  <input
                    id="file-upload"
                    name="file-upload"
                    type="file"
                    accept=".xlsx,.xls"
                    className="sr-only"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                  />
                </label>
                <p className="text-sm text-gray-500 mt-1">
                  or drag and drop
                </p>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Excel files only (.xlsx, .xls)
              </p>
            </div>
            
            {/* Error message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}
            
            {/* Loading state */}
            {isUploading && (
              <div className="text-center">
                <p className="text-sm text-gray-600">Uploading and validating file...</p>
              </div>
            )}
            
            {/* Instructions */}
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <h4 className="text-sm font-medium text-blue-900 mb-2">
                Required Columns:
              </h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Work ID</li>
                <li>• Description</li>
                <li>• Priority</li>
                <li>• Category</li>
                <li>• Estimated Hours</li>
                <li>• Last Service Date</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
