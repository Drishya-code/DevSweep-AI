import '@testing-library/jest-dom'
import { vi } from 'vitest'
import React from 'react'

// Mock react-router-dom
const mockNavigate = vi.fn()
const mockLocation = { pathname: '/' }
const mockParams = {}

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<any>()
  return {
    ...(actual as object),
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
    useParams: () => mockParams,
  }
})

// Mock ViewModeContext
const MockViewModeProvider = ({ children }: { children: React.ReactNode }) => children

vi.mock('../context/ViewModeContext', async (importOriginal) => {
  const actual = await importOriginal<any>()
  return {
    ...(actual as object),
    useViewMode: () => ({ viewMode: 'simple', setViewMode: vi.fn(), toggleViewMode: vi.fn() }),
    ViewModeProvider: MockViewModeProvider,
  }
})

// Mock DevSweepContext - create a factory function to allow customizing the mock
const createMockContext = (overrides = {}) => ({
  currentProject: null,
  setCurrentProject: vi.fn(),
  addScanToHistory: vi.fn(),
  addCleanupToHistory: vi.fn(),
  isScanning: false,
  setIsScanning: vi.fn(),
  demoMode: false,
  currentPlan: null,
  setCurrentPlan: vi.fn(),
  cleanupHistory: [],
  scanHistory: [],
  aiProvider: 'nebius',
  aiModel: 'nvidia/nemotron-3-super-120b-a12b',
  realInferenceAvailable: true,
  ...overrides,
})

let mockContextValue = createMockContext()

const MockProvider = ({ children }: { children: React.ReactNode }) => children

vi.mock('../context/DevSweepContext', async (importOriginal) => {
  const actual = await importOriginal<any>()
  return {
    ...(actual as object),
    useDevSweep: () => mockContextValue,
    DevSweepProvider: MockProvider,
  }
})

// Mock window.fetch
;(globalThis as any).fetch = vi.fn()

// Export mocks for tests to use
export { mockNavigate, createMockContext }
export const setMockContext = (overrides: any) => {
  mockContextValue = createMockContext(overrides)
}
