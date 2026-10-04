import { cn } from '../../utils/helpers';

export interface LoadingStateProps {
  variant?: 'spinner' | 'skeleton' | 'inline' | 'overlay';
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
  skeletonLines?: number;
  skeletonWidth?: 'full' | 'half' | 'quarter';
}

export function LoadingState({
  variant = 'spinner',
  size = 'md',
  text,
  className,
  skeletonLines = 3,
  skeletonWidth = 'full',
}: LoadingStateProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  const widthClasses = {
    full: 'w-full',
    half: 'w-1/2',
    quarter: 'w-1/4',
  };

  if (variant === 'spinner') {
    return (
      <div className={cn('flex items-center justify-center gap-2', className)}>
        <svg
          className={cn('animate-spin text-devsweep-accent', sizeClasses[size])}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        {text && <span className="text-devsweep-textSecondary text-sm">{text}</span>}
      </div>
    );
  }

  if (variant === 'inline') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <svg
          className={cn('animate-spin text-devsweep-accent', sizeClasses[size])}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        {text && <span className="text-devsweep-textSecondary text-sm">{text}</span>}
      </div>
    );
  }

  if (variant === 'overlay') {
    return (
      <div className={cn('fixed inset-0 bg-devsweep-overlay flex items-center justify-center z-modal', className)}>
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-6 flex flex-col items-center gap-3">
          <svg
            className={cn('animate-spin text-devsweep-accent', sizeClasses.lg)}
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="text-devsweep-text">{text || 'Loading...'}</span>
        </div>
      </div>
    );
  }

  // Skeleton variant
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: skeletonLines }).map((_, i) => (
        <div
          key={i}
          className={cn(
            'animate-pulse rounded bg-devsweep-bgTertiary',
            widthClasses[skeletonWidth],
            i === skeletonLines - 1 && skeletonWidth !== 'full' && 'w-1/3'
          )}
          style={{ height: '1rem' }}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

// Skeleton card for content placeholders
export function SkeletonCard({ lines = 4, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-5 space-y-3 animate-pulse', className)}>
      <div className="h-6 w-1/4 bg-devsweep-bgTertiary rounded" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-4 bg-devsweep-bgTertiary rounded" style={{ width: i === lines - 1 ? '60%' : '100%' }} />
      ))}
    </div>
  );
}

// Skeleton table row
export function SkeletonTableRow({ columns = 4, className }: { columns?: number; className?: string }) {
  return (
    <tr className={cn('animate-pulse', className)}>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-devsweep-bgTertiary rounded" style={{ width: '80%' }} />
        </td>
      ))}
    </tr>
  );
}