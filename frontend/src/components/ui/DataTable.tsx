import { useState, useMemo } from 'react';
import { cn } from '../../utils/helpers';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T, index: number) => React.ReactNode;
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyExtractor: (item: T) => string;
  sortable?: boolean;
  defaultSortKey?: string;
  defaultSortDirection?: 'asc' | 'desc';
  onSort?: (key: string, direction: 'asc' | 'desc') => void;
  selectable?: boolean;
  selectedKeys?: Set<string>;
  onSelectionChange?: (keys: Set<string>) => void;
  emptyState?: React.ReactNode;
  loading?: boolean;
  className?: string;
  striped?: boolean;
  hoverable?: boolean;
  compact?: boolean;
}

export function DataTable<T>({
  data,
  columns,
  keyExtractor,
  sortable = false,
  defaultSortKey,
  defaultSortDirection = 'asc',
  onSort,
  selectable = false,
  selectedKeys = new Set(),
  onSelectionChange,
  emptyState,
  loading = false,
  className,
  striped = true,
  hoverable = true,
  compact = false,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState(defaultSortKey || '');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>(defaultSortDirection);

  const sortedData = useMemo(() => {
    if (!sortKey || !sortable) return data;
    return [...data].sort((a, b) => {
      const column = columns.find(c => c.key === sortKey);
      if (!column || !column.render) return 0;
      
      const aVal = column.render(a, 0);
      const bVal = column.render(b, 0);
      
      const aStr = typeof aVal === 'string' ? aVal : String(aVal);
      const bStr = typeof bVal === 'string' ? bVal : String(bVal);
      
      const comparison = aStr.localeCompare(bStr, undefined, { numeric: true });
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [data, sortKey, sortDirection, columns, sortable]);

  const handleSort = (key: string) => {
    if (!sortable) return;
    const column = columns.find(c => c.key === key);
    if (!column?.sortable) return;

    if (sortKey === key) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
    onSort?.(key, sortKey === key && sortDirection === 'asc' ? 'desc' : 'asc');
  };

  const handleSelectAll = () => {
    if (selectedKeys.size === data.length) {
      onSelectionChange?.(new Set());
    } else {
      onSelectionChange?.(new Set(data.map(keyExtractor)));
    }
  };

  const handleSelectRow = (key: string) => {
    const newSelection = new Set(selectedKeys);
    if (newSelection.has(key)) {
      newSelection.delete(key);
    } else {
      newSelection.add(key);
    }
    onSelectionChange?.(newSelection);
  };

  if (loading) {
    return (
      <div className={cn('bg-devsweep-bgSecondary border border-devsweep-border rounded-xl overflow-hidden', className)}>
        <div className="animate-pulse space-y-4 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 bg-devsweep-bgTertiary rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className={cn('bg-devsweep-bgSecondary border border-devsweep-border rounded-xl', className)}>
        {emptyState || (
          <div className="p-12 text-center text-devsweep-textMuted">
            No data available
          </div>
        )}
      </div>
    );
  }

  const cellPadding = compact ? 'px-3 py-2' : 'px-4 py-3';
  const headerPadding = compact ? 'px-3 py-2' : 'px-4 py-3';

  return (
    <div className={cn('bg-devsweep-bgSecondary border border-devsweep-border rounded-xl overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-devsweep-border bg-devsweep-bgTertiary/50">
              {selectable && (
                <th scope="col" className={cn('w-12', headerPadding)}>
                  <input
                    type="checkbox"
                    checked={selectedKeys.size === data.length && data.length > 0}
                    onChange={handleSelectAll}
                    className="w-4 h-4 rounded border-devsweep-border text-devsweep-accent focus:ring-devsweep-accent"
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={column.sortable && sortable ? (sortKey === column.key ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none') : undefined}
                  className={cn(
                    'text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider',
                    headerPadding,
                    column.align && `text-${column.align}`,
                    column.width && `w-[${column.width}]`,
                    column.className
                  )}
                  style={{ width: column.width }}
                >
                  <div className="flex items-center gap-1.5">
                    {column.sortable && sortable && (
                      <button type="button" onClick={() => handleSort(column.key)} className="flex items-center gap-1.5 text-left hover:text-devsweep-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent" aria-label={`Sort by ${column.header}`}>
                        <span>{column.header}</span>
                        <span className="flex flex-col" aria-hidden="true">
                          {sortKey === column.key ? (
                            sortDirection === 'asc' ? <ChevronUp className="w-3 h-3 text-devsweep-accent" /> : <ChevronDown className="w-3 h-3 text-devsweep-accent" />
                          ) : <ChevronsUpDown className="w-3 h-3 text-devsweep-textMuted" />}
                        </span>
                      </button>
                    )}
                    {!(column.sortable && sortable) && (
                      <span>{column.header}</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedData.map((item, index) => {
              const key = keyExtractor(item);
              const isSelected = selectedKeys.has(key);
              return (
                <tr
                  key={key}
                  className={cn(
                    'border-b border-devsweep-border/50 transition-colors',
                    striped && index % 2 === 1 && 'bg-devsweep-bgTertiary/30',
                    hoverable && 'hover:bg-devsweep-bgTertiary/50',
                    isSelected && 'bg-devsweep-accent/5',
                    compact && 'h-10'
                  )}
                >
                  {selectable && (
                    <td className={cn('w-12', cellPadding)}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleSelectRow(key)}
                        className="w-4 h-4 rounded border-devsweep-border text-devsweep-accent focus:ring-devsweep-accent"
                        aria-label={`Select row ${index + 1}`}
                      />
                    </td>
                  )}
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={cn(
                        cellPadding,
                        'text-sm text-devsweep-text',
                        column.align && `text-${column.align}`,
                        column.className
                      )}
                    >
                      {column.render ? column.render(item, index) : String((item as any)[column.key])}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {data.length > 0 && (
        <div className="px-4 py-3 border-t border-devsweep-border bg-devsweep-bgTertiary/50 flex items-center justify-between text-xs text-devsweep-textMuted">
          <span>Showing {data.length} item{data.length !== 1 ? 's' : ''}</span>
          {selectable && selectedKeys.size > 0 && (
            <span>{selectedKeys.size} selected</span>
          )}
        </div>
      )}
    </div>
  );
}
