import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { Sidebar } from './Sidebar'

describe('mobile navigation drawer', () => {
  it('focuses its close control, supports Escape, and closes on navigation', () => {
    const onClose = vi.fn()
    const onNavigate = vi.fn()
    render(<MemoryRouter><Sidebar mobileOpen onClose={onClose} onNavigate={onNavigate} /></MemoryRouter>)
    const close = screen.getByRole('button', { name: 'Close navigation menu' })
    expect(close).toHaveFocus()
    fireEvent.keyDown(close, { key: 'Tab', shiftKey: true })
    expect(screen.getByRole('link', { name: /Settings/ })).toHaveFocus()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('link', { name: /Projects/ }))
    expect(onNavigate).toHaveBeenCalledOnce()
  })
})
