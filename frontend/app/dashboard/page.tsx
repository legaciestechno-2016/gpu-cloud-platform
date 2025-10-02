'use client'

import { useState } from 'react'
import { Cpu, DollarSign, Clock, Activity } from 'lucide-react'

export default function Dashboard() {
  const [instances] = useState([
    { id: 1, name: 'Llama-3-Training', gpu: 'A100', status: 'running', cost: '$12.50' },
    { id: 2, name: 'SD-XL-Inference', gpu: 'T4', status: 'paused', cost: '$0.00' },
  ])

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <span className="text-2xl font-bold text-blue-600">GPUCloud Dashboard</span>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center">
              <Cpu className="w-8 h-8 text-blue-600 mr-4" />
              <div>
                <p className="text-sm text-gray-600">Active GPUs</p>
                <p className="text-2xl font-bold">2</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center">
              <DollarSign className="w-8 h-8 text-green-600 mr-4" />
              <div>
                <p className="text-sm text-gray-600">Today Cost</p>
                <p className="text-2xl font-bold">$12.50</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center">
              <Clock className="w-8 h-8 text-purple-600 mr-4" />
              <div>
                <p className="text-sm text-gray-600">Saved (AutoPause)</p>
                <p className="text-2xl font-bold">$38.40</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center">
              <Activity className="w-8 h-8 text-orange-600 mr-4" />
              <div>
                <p className="text-sm text-gray-600">Uptime</p>
                <p className="text-2xl font-bold">99.9%</p>
              </div>
            </div>
          </div>
        </div>

        {/* Instances */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b">
            <h2 className="text-xl font-semibold">GPU Instances</h2>
          </div>
          <div className="p-6">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-600 border-b">
                  <th className="pb-2">Name</th>
                  <th className="pb-2">GPU</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Cost/Hour</th>
                </tr>
              </thead>
              <tbody>
                {instances.map((instance) => (
                  <tr key={instance.id} className="border-b">
                    <td className="py-3">{instance.name}</td>
                    <td className="py-3">{instance.gpu}</td>
                    <td className="py-3">
                      <span className={`px-2 py-1 rounded text-sm ${
                        instance.status === 'running' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {instance.status}
                      </span>
                    </td>
                    <td className="py-3">{instance.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}