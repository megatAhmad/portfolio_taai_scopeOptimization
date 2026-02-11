/**
 * Process Page - Step 4
 */

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';

export const ProcessPage: React.FC = () => {
  return (
    <div>
      <Card>
        <CardHeader>
          <CardTitle>Process Data</CardTitle>
          <CardDescription>
            Run categorization with AI justifications
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">Processing functionality coming soon...</p>
        </CardContent>
      </Card>
    </div>
  );
};
