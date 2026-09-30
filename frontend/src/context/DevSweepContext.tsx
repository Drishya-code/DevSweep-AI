import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { ScanResponse } from '../types/api'

interface DevSweepContextType {
  // State
  currentProject: ScanResponse | null
  scanHistory: ScanResponse[]
  cleanupPlans: any[]
  cleanupHistory: any[]
  isScanning: boolean
  isCleaning: boolean
  aiProvider: string
  aiModel: string
  demoMode: boolean
  
  // Actions
  setCurrentProject: (project: ScanResponse | null) => void
  addScanToHistory: (scan: ScanResponse) => void
  setIsScanning: (scanning: boolean) => void
  setIsCleaning: (cleaning: boolean) => void
  setDemoMode: (demo: boolean) => void
}

const DevSweepContext = createContext<DevSweepContextType | undefined>(undefined)

export function DevSweepProvider({ children }: { children: ReactNode }) {
  const [currentProject, setCurrentProject] = useState<ScanResponse | null>(null)
  const [scanHistory, setScanHistory] = useState<ScanResponse[]>([])
  const [cleanupPlans, setCleanupPlans] = useState<any[]>([])
  const [cleanupHistory, setCleanupHistory] = useState<any[]>([])
  const [isScanning, setIsScanning] = useState(false)
  const [isCleaning, setIsCleaning] = useState(false)
  const [aiProvider, setAiProvider] = useState('mock')
  const [aiModel, setAiModel] = useState('devsweep-mock')
  const [demoMode, setDemoMode] = useState(false)

  // Load config on mount
  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        setDemoMode(data.demo_mode)
      })
      .catch(() => {})
  }, [])

  const addScanToHistory = (scan: ScanResponse) => {
    setScanHistory(prev => [scan, ...prev.slice(0, 49)]) // Keep last 50
  }

  return (
    <DevSweepContext.Provider value={{
      currentProject,
      scanHistory,
      cleanupPlans,
      cleanupHistory,
      isScanning,
      isCleaning,
      aiProvider,
      aiModel,
      demoMode,
      setCurrentProject,
      addScanToHistory,
      setIsScanning,
      setIsCleaning,
      setDemoMode,
    }}>
      {children}
    </DevSweepContext.Provider>
  )
}

export function useDevSweep() {
  const context = useContext(DevSweepContext)
  if (!context) {
    throw new Error('useDevSweep must be used within a DevSweepProvider')
  }
  return context
}