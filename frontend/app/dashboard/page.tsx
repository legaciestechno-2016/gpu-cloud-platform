'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Cpu, DollarSign, TrendingDown, Clock, 
  Play, Pause, Trash2, Plus, Activity
} from 'lucide-react'
import Link from 'next/link'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface Instance {
  id: string
  name: string
  gpu_type: string
  status: 'running' | 'paused' | 'stopped'
  cost_per_hour: number
  total_cost: number
  savings: number
  gpu_utilization: number
  uptime: string
  public_ip: string
}

export default function Dashboard() {
  const [instances, setInstances] = useState<Instance[]>([
    {
      id: 'gpu-1',
      name: 'Llama-3-Training',
      gpu_type: 'A100',
      status: 'running',
      cost_per_hour: 3.99,
      total_cost: 127.68,
      savings: 89.38,
      gpu_utilization: 78,
      uptime: '32h 15m',
      public_ip: '20.124.56.78'
    },
    {
      id: 'gpu-2',
      name: 'Stable-Diffusion-XL',
      gpu_type: 'A10G',
      status: 'paused',
      cost_per_hour: 1.99,
      total_cost: 45.77,
      savings: 32.04,
      gpu_utilization: 0,
      uptime: '23h 0m',
      public_ip: '20.124.56.79'
    },
    {
      id: 'gpu-3',
      name: 'Jupyter-Notebook',
      gpu_type: 'T4',
      status: 'running',
      cost_per_hour: 0.99,
      total_cost: 15.84,
      savings: 11.09,
      gpu_utilization: 12,
      uptime: '16h 0m',
      public_ip: '20.124.56.80'
    }
  ])
  
  const [totalSavings] = useState(132.51)
  const [creditsRemaining] = useState(372.55)
  
  // Mock usage data for chart
  const usageData = [
    { day: 'Mon', cost: 45, saved: 31 },
    { day: 'Tue', cost: 52, saved: 36 },
    { day: 'Wed', cost: 38, saved: 27 },
    { day: 'Thu', cost: 61, saved: 43 },
    { day: 'Fri', cost: 49, saved: 34 },
    { day: 'Sat', cost: 28, saved: 20 },
    { day: 'Sun', cost: 35, saved: 25 }
  ]
  
  const handleInstanceAction = (id: string, action: 'pause' | 'resume' | 'delete') => {
    setInstances(prev => prev.map(instance => {
      if (instance.id === id) {
        if (action === 'pause') {
          return { ...instance, status: 'paused', gpu_utilization: 0 }
        } else if (action === 'resume') {
          return { ...instance, status: 'running', gpu_utilization: Math.random() * 100 }
        }
      }
      return instance
    }))
    
    if (action === 'delete') {
      setInstances(prev => prev.filter(i => i.id !== id))
    }
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center space-x-8">
              <Link href="/" className="text-2xl font-bold gradient-text">
                GPUCloud
              </Link>
              <nav className="flex space-x-4">
                <Link href="/dashboard" className="text-primary-600 font-medium">
                  Dashboard
                </Link>
                <Link href="/templates" className="text-gray-600 hover:text-gray-900">
                  Templates
                </Link>
                <Link href="/billing" className="text-gray-600 hover:text-gray-900">
                  Billing
                </Link>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Credits: <span className="font-bold text-primary-600">${creditsRemaining}</span>
              </span>
              <button className="text-gray-600 hover:text-gray-900">
                Settings
              </button>
            </div>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl p-6 shadow-sm"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-600">Active GPUs</span>
              <Cpu className="w-5 h-5 text-primary-600" />
            </div>
            <p className="text-2xl font-bold">{instances.length}</p>
            <p className="text-sm text-gray-500">
              {instances.filter(i => i.status === 'running').length} running
            </p>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-xl p-6 shadow-sm"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-600">Total Saved</span>
              <TrendingDown className="w-5 h-5 text-success" />
            </div>
            <p className="text-2xl font-bold text-success">${totalSavings}</p>
            <p className="text-sm text-gray-500">This month</p>
            <div className="mt-2 bg-success/10 text-success text-xs px-2 py-1 rounded-full inline-block">
              AutoPause Active
            </div>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-xl p-6 shadow-sm"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-600">Current Spend</span>
              <DollarSign className="w-5 h-5 text-gray-600" />
            </div>
            <p className="text-2xl font-bold">
              ${instances.reduce((acc, i) => acc + i.total_cost, 0).toFixed(2)}
            </p>
            <p className="text-sm text-gray-500">vs ${(instances.reduce((acc, i) => acc + i.total_cost, 0) * 3).toFixed(0)} on AWS</p>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-xl p-6 shadow-sm"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-600">AutoPaused</span>
              <Pause className="w-5 h-5 text-secondary-600" />
            </div>
            <p className="text-2xl font-bold">
              {instances.filter(i => i.status === 'paused').length}
            </p>
            <p className="text-sm text-gray-500">Saving money</p>
          </motion.div>
        </div>
        
        {/* Usage Chart */}
        <div className="bg-white rounded-xl p-6 shadow-sm mb-8">
          <h2 className="text-lg font-semibold mb-4">7-Day Usage & Savings</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={usageData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="cost" stroke="#3b82f6" name="Cost" />
              <Line type="monotone" dataKey="saved" stroke="#10b981" name="Saved" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        {/* Active Instances */}
        <div className="bg-white rounded-xl shadow-sm">
          <div className="p-6 border-b flex justify-between items-center">
            <h2 className="text-lg font-semibold">Active Instances</h2>
            <Link 
              href="/deploy"
              className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition flex items-center"
            >
              <Plus className="w-4 h-4 mr-2" />
              Deploy GPU
            </Link>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Instance
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    GPU
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Utilization
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Cost/hr
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Saved
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {instances.map((instance) => (
                  <tr key={instance.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div>
                        <div className="font-medium">{instance.name}</div>
                        <div className="text-sm text-gray-500">{instance.public_ip}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 text-xs rounded-full bg-primary-100 text-primary-700">
                        {instance.gpu_type}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        instance.status === 'running' 
                          ? 'bg-green-100 text-green-700'
                          : instance.status === 'paused'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}>
                        {instance.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <Activity className="w-4 h-4 mr-2 text-gray-400" />
                        <span>{instance.gpu_utilization.toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      ${instance.cost_per_hour}/hr
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-success font-medium">
                        ${instance.savings.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex space-x-2">
                        {instance.status === 'running' ? (
                          <button
                            onClick={() => handleInstanceAction(instance.id, 'pause')}
                            className="p-1 hover:bg-gray-100 rounded"
                            title="Pause"
                          >
                            <Pause className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleInstanceAction(instance.id, 'resume')}
                            className="p-1 hover:bg-gray-100 rounded"
                            title="Resume"
                          >
                            <Play className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => handleInstanceAction(instance.id, 'delete')}
                          className="p-1 hover:bg-gray-100 rounded text-red-600"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}