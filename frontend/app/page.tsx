'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { 
  Zap, DollarSign, Clock, Shield, Rocket, 
  ChevronRight, Check, TrendingDown, Cpu
} from 'lucide-react'

export default function LandingPage() {
  const [savings, setSavings] = useState(0)
  const [deployTime] = useState(10)

  useEffect(() => {
    const interval = setInterval(() => {
      setSavings(prev => {
        if (prev < 70) return prev + 1
        return 70
      })
    }, 20)
    return () => clearInterval(interval)
  }, [])

  const features = [
    {
      icon: <TrendingDown className="w-6 h-6" />,
      title: "AutoPause™ Technology",
      description: "Automatically pause idle GPUs and save 70% on costs"
    },
    {
      icon: <Zap className="w-6 h-6" />,
      title: "10-Second Deploy",
      description: "Fastest GPU deployment in the industry"
    },
    {
      icon: <Rocket className="w-6 h-6" />,
      title: "One-Click Templates",
      description: "Deploy Llama 3, Stable Diffusion, and more instantly"
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <span className="text-2xl font-bold text-blue-600">GPUCloud</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/dashboard" className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">
                Start Free
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-20 pb-32 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            Deploy GPU in <span className="text-blue-600">{deployTime} Seconds</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Save <span className="text-green-600 font-bold text-2xl">{savings}%</span> on GPU costs 
            with AutoPause™ technology. The fastest and cheapest way to run AI models.
          </p>
          
          <div className="flex justify-center space-x-4 mb-12">
            <Link href="/dashboard" className="bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition flex items-center">
              Start Free - No Credit Card
              <ChevronRight className="ml-2" />
            </Link>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8 max-w-4xl mx-auto">
            <div className="grid grid-cols-3 gap-8">
              <div>
                <p className="text-gray-500 mb-2">Money Saved Today</p>
                <p className="text-4xl font-bold text-green-600">
                  ${(savings * 142).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-gray-500 mb-2">GPUs Running</p>
                <p className="text-4xl font-bold text-blue-600">847</p>
              </div>
              <div>
                <p className="text-gray-500 mb-2">AutoPaused Now</p>
                <p className="text-4xl font-bold text-purple-600">312</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Why Teams Choose GPUCloud
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="bg-gray-50 p-6 rounded-lg">
                <div className="text-blue-600 mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p>© 2025 GPUCloud. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}