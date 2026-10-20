import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RealWorkspace } from './RealWorkspace'

describe('RealWorkspace permission flow', () => {
  it('explains when the browser does not support folder selection', async () => {
    render(<RealWorkspace />)
    fireEvent.click(screen.getByRole('button', { name: /choose folder/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/does not support secure folder selection/i)
  })

  it('stops after the browser denies read/write permission', async () => {
    Object.defineProperty(window, 'showDirectoryPicker', { configurable: true, value: vi.fn().mockResolvedValue({ name: 'Selected', requestPermission: vi.fn().mockResolvedValue('denied') }) })
    render(<RealWorkspace />)
    fireEvent.click(screen.getByRole('button', { name: /choose folder/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/access was denied/i)
    expect(screen.queryByText('Selected')).not.toBeInTheDocument()
  })
})
