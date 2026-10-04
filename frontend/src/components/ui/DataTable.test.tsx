import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { DataTable } from './DataTable'

const rows = [{ id: 'b', name: 'Beta' }, { id: 'a', name: 'Alpha' }]
const columns = [{ key: 'name', header: 'Name', sortable: true, render: (row: typeof rows[number]) => row.name }]

describe('DataTable accessibility', () => {
  it('uses native table semantics and supports keyboard sorting with aria-sort', async () => {
    const user = userEvent.setup()
    const { container } = render(<DataTable data={rows} columns={columns} keyExtractor={row => row.id} sortable />)
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(container.querySelector('[role="grid"]')).toBeNull()
    const header = screen.getByRole('columnheader', { name: /Name/ })
    expect(header).toHaveAttribute('aria-sort', 'none')
    const sortButton = screen.getByRole('button', { name: 'Sort by Name' })
    sortButton.focus()
    await user.keyboard('{Enter}')
    expect(header).toHaveAttribute('aria-sort', 'ascending')
    expect(screen.getAllByRole('row')[1]).toHaveTextContent('Alpha')
    fireEvent.click(sortButton)
    expect(header).toHaveAttribute('aria-sort', 'descending')
  })

  it('omits sorting affordances when sorting is disabled', () => {
    render(<DataTable data={rows} columns={columns} keyExtractor={row => row.id} />)
    expect(screen.queryByRole('button', { name: /Sort by/ })).not.toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Name' })).not.toHaveAttribute('aria-sort')
  })
})
