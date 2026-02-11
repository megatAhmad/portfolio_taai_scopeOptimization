/**
 * Rules Page - Step 2
 */

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';

export const RulesPage: React.FC = () => {
  return (
    <div>
      <Card>
        <CardHeader>
          <CardTitle>Configure Rules</CardTitle>
          <CardDescription>
            Define rules for categorizing maintenance work
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">Rules configuration coming soon...</p>
        </CardContent>
      </Card>
    </div>
  );
};
