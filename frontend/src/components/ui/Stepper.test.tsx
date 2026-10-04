import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Stepper } from './Stepper'

describe('Stepper responsive layout', () => {
  it('preserves ordered numbered steps and hides long descriptions below the small breakpoint', () => {
    const { container } = render(<Stepper steps={[
      { id: 'scan', label: 'Scan', description: 'Select and scan a project' },
      { id: 'review', label: 'Review', description: 'Review cleanup candidates' },
      { id: 'confirm', label: 'Confirm', description: 'Approve and execute cleanup' },
    ]} currentStep="scan" />)
    expect(screen.getByRole('navigation', { name: 'Progress steps' })).toBeInTheDocument()
    expect(container.querySelectorAll('.basis-0')).toHaveLength(3)
    expect(container.querySelectorAll('p.hidden')).toHaveLength(3)
    expect(screen.getByRole('button', { name: 'Step 1: Scan' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Step 2: Review' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Step 3: Confirm' })).toBeInTheDocument()
  })
})
