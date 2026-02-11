/**
 * Results Page - Step 5
 */

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';

export const ResultsPage: React.FC = () => {
  return (
    <div>
      <Card>
        <CardHeader>
          <CardTitle>View Results</CardTitle>
          <CardDescription>
            Review categorization results and export data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">Results display coming soon...</p>
        </CardContent>
      </Card>
    </div>
  );
};
