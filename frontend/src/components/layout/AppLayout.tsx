/**
 * Main application layout
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import { Stepper, Step } from './Stepper';
import { useAppStore } from '@/store/useAppStore';

const steps: Step[] = [
  { id: 0, name: 'Upload', description: 'Upload data file' },
  { id: 1, name: 'Rules', description: 'Configure rules' },
  { id: 2, name: 'Preview', description: 'Preview workflow' },
  { id: 3, name: 'Process', description: 'Process data' },
  { id: 4, name: 'Results', description: 'View results' },
];

export const AppLayout: React.FC = () => {
  const currentStep = useAppStore((state) => state.currentStep);
  const setCurrentStep = useAppStore((state) => state.setCurrentStep);
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              Maintenance Work Categorization System
            </h1>
            <div className="text-sm text-gray-500">
              MWCS v2.0
            </div>
          </div>
        </div>
      </header>
      
      {/* Stepper */}
      <div className="bg-white border-b">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Stepper
            steps={steps}
            currentStep={currentStep}
            onStepClick={setCurrentStep}
          />
        </div>
      </div>
      
      {/* Main content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t mt-auto">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            © 2026 MWCS. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};
