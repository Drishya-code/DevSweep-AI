import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TopBar } from './TopBar'
import { setMockContext } from '../test/setup'

const viewMode = vi.hoisted(() => ({ mode: 'simple' as 'simple' | 'technical', setMode: vi.fn() }))
vi.mock('../context/ViewModeContext', async importOriginal => {
  const actual = await importOriginal<typeof import('../context/ViewModeContext')>()
  return { ...actual, useViewMode: () => ({ viewMode: viewMode.mode, setViewMode: viewMode.setMode, toggleViewMode: vi.fn() }) }
})

describe('TopBar', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    viewMode.mode = 'simple'
    viewMode.setMode.mockClear()
    setMockContext({})
    window.matchMedia = vi.fn().mockReturnValue({ matches: false })
  })

  it('exposes both view choices in the compact header and sets the selected mode explicitly', () => {
    const openNavigation = vi.fn()
    render(<TopBar onOpenNavigation={openNavigation} />)
    const group = screen.getByRole('group', { name: 'View mode' })
    expect(group).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Simple' })).toHaveAttribute('aria-pressed', 'true')
    const technical = screen.getByRole('button', { name: 'Technical' })
    expect(screen.getByText('Simple')).toHaveClass('text-[10px]')
    expect(screen.getByText('Technical')).toHaveClass('text-[10px]')
    expect(technical).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(technical)
    expect(viewMode.setMode).toHaveBeenCalledWith('technical')
    fireEvent.click(screen.getByRole('button', { name: 'Open navigation menu' }))
    expect(openNavigation).toHaveBeenCalledOnce()
  })

  it('reflects Technical View as selected when active', () => {
    viewMode.mode = 'technical'
    render(<TopBar />)
    expect(screen.getByRole('button', { name: 'Technical' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Simple' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('switches the shared theme attribute and persists the selection', () => {
    localStorage.setItem('devsweep-theme', 'dark')
    render(<TopBar />)
    fireEvent.click(screen.getByRole('button', { name: 'Switch to light mode' }))
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    expect(localStorage.getItem('devsweep-theme')).toBe('light')
    expect(screen.getByText('Simple')).toBeVisible()
    expect(screen.getByText('Technical')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark mode' }))
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(localStorage.getItem('devsweep-theme')).toBe('dark')
    expect(screen.getByText('Simple')).toBeVisible()
    expect(screen.getByText('Technical')).toBeVisible()
  })

  it('labels candidate size as candidate data, not total storage usage', () => {
    setMockContext({ currentProject: { project_path: '/test/project', framework: 'react', has_git: true, git_clean: true, cleanup_candidates: [{ size_bytes: 1024, risk: 'SAFE' }], total_recoverable_human: '1 KB' } })
    render(<TopBar />)
    expect(screen.getByText(/Candidate size:/)).toBeInTheDocument()
    expect(screen.queryByText(/Used:/)).not.toBeInTheDocument()
  })
})
