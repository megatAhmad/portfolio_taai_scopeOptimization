/**
 * Stepper component for workflow navigation
 */

import React from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface Step {
  id: number;
  name: string;
  description: string;
}

export interface StepperProps {
  steps: Step[];
  currentStep: number;
  onStepClick?: (step: number) => void;
}

export const Stepper: React.FC<StepperProps> = ({ steps, currentStep, onStepClick }) => {
  return (
    <nav aria-label="Progress">
      <ol className="flex items-center">
        {steps.map((step, stepIdx) => {
          const isCompleted = step.id < currentStep;
          const isCurrent = step.id === currentStep;
          const isClickable = step.id <= currentStep && onStepClick;
          
          return (
            <li
              key={step.id}
              className={cn(
                'relative',
                stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-20' : ''
              )}
            >
              {/* Connector line */}
              {stepIdx !== steps.length - 1 && (
                <div
                  className="absolute left-4 top-4 -ml-px mt-0.5 h-0.5 w-full"
                  aria-hidden="true"
                >
                  <div
                    className={cn(
                      'h-full w-full',
                      isCompleted ? 'bg-blue-600' : 'bg-gray-300'
                    )}
                  />
                </div>
              )}
              
              {/* Step button */}
              <button
                onClick={() => isClickable && onStepClick(step.id)}
                disabled={!isClickable}
                className={cn(
                  'group relative flex items-center',
                  isClickable ? 'cursor-pointer' : 'cursor-default'
                )}
              >
                <span className="flex h-9 items-center">
                  <span
                    className={cn(
                      'relative z-10 flex h-8 w-8 items-center justify-center rounded-full',
                      isCompleted && 'bg-blue-600',
                      isCurrent && 'border-2 border-blue-600 bg-white',
                      !isCompleted && !isCurrent && 'border-2 border-gray-300 bg-white'
                    )}
                  >
                    {isCompleted ? (
                      <Check className="h-5 w-5 text-white" />
                    ) : (
                      <span
                        className={cn(
                          'text-sm font-semibold',
                          isCurrent ? 'text-blue-600' : 'text-gray-500'
                        )}
                      >
                        {step.id}
                      </span>
                    )}
                  </span>
                </span>
                <span className="ml-4 flex min-w-0 flex-col">
                  <span
                    className={cn(
                      'text-sm font-medium',
                      isCurrent ? 'text-blue-600' : 'text-gray-900'
                    )}
                  >
                    {step.name}
                  </span>
                  <span className="text-sm text-gray-500">{step.description}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
