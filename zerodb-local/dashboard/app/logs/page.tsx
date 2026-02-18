'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Activity } from 'lucide-react'

export default function LogsPage() {
    return (
        <div className="p-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2">Event Logs</h1>
                <p className="text-gray-600">View real-time event stream and system logs</p>
            </div>
            <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                    <Activity className="h-12 w-12 text-gray-400 mb-4" />
                    <p className="text-gray-500">Log viewer coming soon</p>
                </CardContent>
            </Card>
        </div>
    )
}
