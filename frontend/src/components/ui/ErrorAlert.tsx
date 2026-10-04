import { cn } from '../../utils/helpers';
import { X, AlertCircle, AlertTriangle, CheckCircle, Info } from 'lucide-react';

export interface ErrorAlertProps {
  title?: string;
  message: string;
  variant?: 'error' | 'warning' | 'success' | 'info';
  dismissible?: boolean;
  onDismiss?: () => void;
  className?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const variantConfig = {
  error: {
    icon: AlertCircle,
    bg: 'bg-devsweep-danger/10',
    border: 'border-devsweep-danger/20',
    text: 'text-devsweep-danger',
    iconColor: 'text-devsweep-danger',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-devsweep-warning/10',
    border: 'border-devsweep-warning/20',
    text: 'text-devsweep-warning',
    iconColor: 'text-devsweep-warning',
  },
  success: {
    icon: CheckCircle,
    bg: 'bg-devsweep-success/10',
    border: 'border-devsweep-success/20',
    text: 'text-devsweep-success',
    iconColor: 'text-devsweep-success',
  },
  info: {
    icon: Info,
    bg: 'bg-devsweep-accent/10',
    border: 'border-devsweep-accent/20',
    text: 'text-devsweep-accent',
    iconColor: 'text-devsweep-accent',
  },
};

export function ErrorAlert({
  title,
  message,
  variant = 'error',
  dismissible = false,
  onDismiss,
  className,
  action,
}: ErrorAlertProps) {
  const config = variantConfig[variant];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-lg border',
        config.bg,
        config.border,
        config.text,
        className
      )}
      role="alert"
    >
      <Icon className={cn('w-5 h-5 flex-shrink-0 mt-0.5', config.iconColor)} aria-hidden="true" />
      <div className="flex-1 min-w-0">
        {title && <h4 className="font-medium mb-1">{title}</h4>}
        <p className="text-sm">{message}</p>
        {action && (
          <button
            onClick={action.onClick}
            className="mt-2 text-sm underline hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-devsweep-accent"
          >
            {action.label}
          </button>
        )}
      </div>
      {dismissible && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 p-1 hover:bg-black/10 rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

// Inline error for forms
export function InlineError({ message, className }: { message: string; className?: string }) {
  return (
    <div className={cn('flex items-center gap-2 text-devsweep-danger text-sm', className)} role="alert">
      <AlertCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

// Toast-style notification
export interface ToastProps extends ErrorAlertProps {
  duration?: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

export function Toast({ duration = 5000, ...props }: ToastProps) {
  // In a real app, this would be managed by a toast context
  // For now, just render as ErrorAlert
  return <ErrorAlert {...props} />;
}
