/**
 * Preview Page - Step 3
 */

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';

export const PreviewPage: React.FC = () => {
  return (
    <div>
      <Card>
        <CardHeader>
          <CardTitle>Preview Workflow</CardTitle>
          <CardDescription>
            Review rule flowchart and sample evaluations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">Preview functionality coming soon...</p>
        </CardContent>
      </Card>
    </div>
  );
};
