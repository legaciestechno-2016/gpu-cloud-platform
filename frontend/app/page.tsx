'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { 
  Zap, DollarSign, Clock, Shield, Rocket, 
  ChevronRight, Check, TrendingDown, Cpu
} from 'lucide-react'
import CostCalculator from '@/components/CostCalculator'
import FeatureCard from '@/components/FeatureCard'

export default function LandingPage() {
  const [savings, setSavings] = useState(0)
  const [deployTime, setDeployTime] = useState(10)

  useEffect(() => {
    // Animate savings counter
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

  const pricingTiers = [
    {
      name: "Starter",
      price: "$299",
      credits: "400 GPU Credits",
      features: [
        "AutoPause included",
        "All GPU types",
        "Email support",
        "99.9% SLA"
      ]
    },
    {
      name: "Business",
      price: "$999",
      credits: "1500 GPU Credits",
      popular: true,
      features: [
        "Everything in Starter",
        "Priority support",
        "Custom templates",
        "Team collaboration",
        "API access"
      ]
    },
    {
      name: "Enterprise",
      price: "Custom",
      credits: "Unlimited",
      features: [
        "Everything in Business",
        "24/7 phone support",
        "Custom SLA",
        "Private cloud option",
        "Volume discounts"
      ]
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <span className="text-2xl font-bold gradient-text">GPUCloud</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/templates" className="text-gray-700 hover:text-primary-600">
                Templates
              </Link>
              <Link href="/pricing" className="text-gray-700 hover:text-primary-600">
                Pricing
              </Link>
              <Link href="/dashboard" className="text-gray-700 hover:text-primary-600">
                Dashboard
              </Link>
              <Link 
                href="/dashboard" 
                className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition"
              >
                Start Free
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-20 pb-32 px-4">
        <div className="max-w-7xl mx-auto">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center"
          >
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
              Deploy GPU in <span className="gradient-text">{deployTime} Seconds</span>
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
              Save <span className="text-success font-bold text-2xl">{savings}%</span> on GPU costs 
              with AutoPause™ technology. The fastest and cheapest way to run AI models.
            </p>
            
            {/* CTA Buttons */}
            <div className="flex justify-center space-x-4 mb-12">
              <Link 
                href="/dashboard"
                className="bg-primary-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-primary-700 transition flex items-center"
              >
                Start Free - No Credit Card
                <ChevronRight className="ml-2" />
              </Link>
              <button className="border-2 border-primary-600 text-primary-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-primary-50 transition">
                Watch Demo
              </button>
            </div>

            {/* Live Savings Counter */}
            <div className="bg-white rounded-2xl shadow-xl p-8 max-w-4xl mx-auto">
              <div className="grid grid-cols-3 gap-8">
                <div>
                  <p className="text-gray-500 mb-2">Money Saved Today</p>
                  <p className="text-4xl font-bold text-success animate-savings">
                    ${(savings * 142).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 mb-2">GPUs Running</p>
                  <p className="text-4xl font-bold text-primary-600">847</p>
                </div>
                <div>
                  <p className="text-gray-500 mb-2">AutoPaused Now</p>
                  <p className="text-4xl font-bold text-secondary-600">312</p>
                </div>
              </div>
            </div>
          </motion.div>
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
              <FeatureCard key={index} {...feature} />
            ))}
          </div>
        </div>
      </section>

      {/* Cost Calculator */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Calculate Your Savings
          </h2>
          <CostCalculator />
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Simple, Transparent Pricing
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {pricingTiers.map((tier, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`bg-white rounded-xl p-8 ${
                  tier.popular ? 'ring-2 ring-primary-600 shadow-xl' : 'shadow-lg'
                }`}
              >
                {tier.popular && (
                  <span className="bg-primary-600 text-white px-3 py-1 rounded-full text-sm">
                    Most Popular
                  </span>
                )}
                <h3 className="text-2xl font-bold mt-4">{tier.name}</h3>
                <p className="text-4xl font-bold mt-4 mb-2">{tier.price}</p>
                <p className="text-gray-600 mb-6">{tier.credits}</p>
                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center">
                      <Check className="w-5 h-5 text-success mr-2" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
                <button className={`w-full py-3 rounded-lg font-semibold transition ${
                  tier.popular 
                    ? 'bg-primary-600 text-white hover:bg-primary-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}>
                  Get Started
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Customer Logos */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4">
          <p className="text-center text-gray-600 mb-8">
            Trusted by AI teams worldwide
          </p>
          <div className="flex justify-center items-center space-x-12 opacity-50">
            {['OpenAI', 'Anthropic', 'Stability', 'Cohere', 'Replicate'].map((company) => (
              <div key={company} className="text-2xl font-bold text-gray-400">
                {company}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <h4 className="text-xl font-bold mb-4">GPUCloud</h4>
              <p className="text-gray-400">
                70% Cheaper. 10 Seconds Faster.
              </p>
            </div>
            <div>
              <h5 className="font-semibold mb-3">Product</h5>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="/features">Features</Link></li>
                <li><Link href="/templates">Templates</Link></li>
                <li><Link href="/pricing">Pricing</Link></li>
              </ul>
            </div>
            <div>
              <h5 className="font-semibold mb-3">Company</h5>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="/about">About</Link></li>
                <li><Link href="/blog">Blog</Link></li>
                <li><Link href="/careers">Careers</Link></li>
              </ul>
            </div>
            <div>
              <h5 className="font-semibold mb-3">Support</h5>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="/docs">Documentation</Link></li>
                <li><Link href="/contact">Contact</Link></li>
                <li><Link href="/status">Status</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>© 2025 GPUCloud. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}