import { cn } from '../../utils/helpers';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary';
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  illustration?: 'scan' | 'project' | 'history' | 'cleanup' | 'restore' | 'agent';
}

const illustrations = {
  scan: (
    <svg viewBox="0 0 64 64" className="w-16 h-16 text-devsweep-textMuted opacity-50" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="8" y="8" width="48" height="48" rx="4" />
      <path d="M16 24h32M16 32h24M16 40h16" strokeLinecap="round" />
      <circle cx="48" cy="16" r="6" />
      <path d="M50 14l3 3" strokeLinecap="round" />
    </svg>
  ),
  project: (
    <svg viewBox="0 0 64 64" className="w-16 h-16 text-devsweep-textMuted opacity-50" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M8 12h48v40H8z" />
      <path d="M8 20h48" />
      <rect x="16" y="28" width="12" height="12" rx="2" />
      <rect x="36" y="28" width="12" height="12" rx="2" />
      <rect x="16" y="44" width="32" height="6" rx="1" />
    </svg>
  ),
  history: (
    <svg viewBox="0 0 64 64" className="w-16 h-16 text-devsweep-textMuted opacity-50" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="32" cy="32" r="24" />
      <path d="M32 16v16l8 8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M16 32h8M48 32h8M32 16v8M32 48v8" strokeLinecap="round" />
    </svg>
  ),
  cleanup: (
    <svg viewBox="0 0 64 64" className="w-16 h-16 text-devsweep-textMuted opacity-50" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M12 12h40v40H12z" />
      <path d="M20 20l24 24M44 20l-24 24" strokeLinecap="round" />
    </svg>
  ),
  restore: (
    <svg viewBox="0 0 64 64" className="w-16 h-16 text-devsweep-textMuted opacity-50" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M32 8a24 24 0 1 0 0 48 24 24 0 0 0 0-48z" />
      <path d="M32 16v16l10 10" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  agent: (
    <svg viewBox="0 0 64 64" className="w-16 h-16 text-devsweep-textMuted opacity-50" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="8" y="12" width="48" height="40" rx="6" />
      <circle cx="22" cy="28" r="4" />
      <circle cx="42" cy="28" r="4" />
      <path d="M20 42c0 4 4 6 12 6s12-2 12-6" strokeLinecap="round" />
      <rect x="28" y="8" width="8" height="4" rx="1" />
    </svg>
  ),
};

export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  className,
  illustration,
}: EmptyStateProps) {
  const illustrationNode = illustration ? illustrations[illustration] : null;

  return (
    <div className={cn('flex flex-col items-center justify-center text-center py-12 px-4', className)}>
      <div className="mb-4" aria-hidden="true">
        {icon || illustrationNode}
      </div>
      <h3 className="text-lg font-semibold text-devsweep-text mb-2">{title}</h3>
      {description && (
        <p className="text-devsweep-textSecondary text-sm max-w-md mb-6">{description}</p>
      )}
      {(action || secondaryAction) && (
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 w-full max-w-md">
          {action && (
            <button
              onClick={action.onClick}
              className={cn(
                'w-full sm:w-auto px-4 py-2 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent focus-visible:ring-offset-2 focus-visible:ring-offset-devsweep-bg',
                action.variant === 'secondary'
                  ? 'bg-devsweep-bgTertiary text-devsweep-text border border-devsweep-border hover:bg-devsweep-bgHover'
                  : 'bg-devsweep-accent text-devsweep-bg hover:bg-devsweep-accentHover'
              )}
            >
              {action.label}
            </button>
          )}
          {secondaryAction && (
            <button
              onClick={secondaryAction.onClick}
              className="w-full sm:w-auto px-4 py-2 rounded-lg font-medium text-devsweep-textSecondary hover:text-devsweep-text transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent focus-visible:ring-offset-2 focus-visible:ring-offset-devsweep-bg"
            >
              {secondaryAction.label}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
