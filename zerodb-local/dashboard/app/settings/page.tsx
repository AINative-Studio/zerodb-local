'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Settings as SettingsIcon } from 'lucide-react'

export default function SettingsPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-gray-600">Configure your ZeroLocal instance</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>System settings and preferences</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="font-medium mb-1">API Endpoint</div>
              <div className="text-sm text-gray-600">http://localhost:8000</div>
            </div>
            <div>
              <div className="font-medium mb-1">Dashboard Port</div>
              <div className="text-sm text-gray-600">3000</div>
            </div>
            <div>
              <div className="font-medium mb-1">Environment</div>
              <div className="text-sm text-gray-600">Local Development</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
