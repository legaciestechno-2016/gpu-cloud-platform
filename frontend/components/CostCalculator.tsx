'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Calculator, TrendingDown } from 'lucide-react'

export default function CostCalculator() {
  const [hours, setHours] = useState(100)
  const [gpuType, setGpuType] = useState('A10G')
  
  const gpuPrices = {
    'T4': { aws: 3.06, ours: 0.99 },
    'A10G': { aws: 5.12, ours: 1.99 },
    'A100': { aws: 12.24, ours: 3.99 }
  }
  
  const awsCost = hours * gpuPrices[gpuType as keyof typeof gpuPrices].aws
  const ourCost = hours * gpuPrices[gpuType as keyof typeof gpuPrices].ours
  const savings = awsCost - ourCost
  const savingsPercent = ((savings / awsCost) * 100).toFixed(0)
  
  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 max-w-4xl mx-auto">
      <div className="grid md:grid-cols-2 gap-8">
        {/* Calculator Inputs */}
        <div>
          <h3 className="text-xl font-semibold mb-4">Your Usage</h3>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              GPU Type
            </label>
            <select 
              value={gpuType}
              onChange={(e) => setGpuType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="T4">NVIDIA T4 (16GB)</option>
              <option value="A10G">NVIDIA A10G (24GB)</option>
              <option value="A100">NVIDIA A100 (80GB)</option>
            </select>
          </div>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Hours per Month: {hours}
            </label>
            <input 
              type="range"
              min="10"
              max="730"
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-sm text-gray-500">
              <span>10 hrs</span>
              <span>730 hrs</span>
            </div>
          </div>
        </div>
        
        {/* Cost Comparison */}
        <div>
          <h3 className="text-xl font-semibold mb-4">Monthly Cost Comparison</h3>
          
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">AWS/Azure</span>
                <span className="text-2xl font-bold text-gray-900">
                  ${awsCost.toFixed(2)}
                </span>
              </div>
            </div>
            
            <div className="bg-primary-50 rounded-lg p-4 border-2 border-primary-500">
              <div className="flex justify-between items-center">
                <span className="text-primary-700 font-semibold">GPUCloud</span>
                <span className="text-2xl font-bold text-primary-600">
                  ${ourCost.toFixed(2)}
                </span>
              </div>
            </div>
            
            <motion.div 
              className="bg-success/10 rounded-lg p-4 border-2 border-success"
              animate={{ scale: [1, 1.02, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <div className="flex justify-between items-center">
                <span className="text-success font-semibold flex items-center">
                  <TrendingDown className="w-5 h-5 mr-2" />
                  Your Savings
                </span>
                <div className="text-right">
                  <span className="text-2xl font-bold text-success">
                    ${savings.toFixed(2)}
                  </span>
                  <span className="block text-sm text-success">
                    {savingsPercent}% cheaper
                  </span>
                </div>
              </div>
            </motion.div>
          </div>
          
          <p className="text-sm text-gray-600 mt-4">
            * Includes AutoPause savings. AWS prices based on on-demand instances.
          </p>
        </div>
      </div>
    </div>
  )
}