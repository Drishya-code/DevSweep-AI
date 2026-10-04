import { forwardRef, ButtonHTMLAttributes } from 'react';
import { cn } from '../../utils/helpers';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success' | 'outline';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      icon,
      iconPosition = 'left',
      fullWidth = false,
      className,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const variantClasses = {
      primary: 'bg-devsweep-accent text-devsweep-bg hover:bg-devsweep-accentHover',
      secondary: 'bg-devsweep-bgTertiary text-devsweep-text border border-devsweep-border hover:bg-devsweep-bgHover',
      ghost: 'text-devsweep-textSecondary hover:text-devsweep-text hover:bg-devsweep-bgTertiary',
      danger: 'bg-devsweep-danger/10 text-devsweep-danger border border-devsweep-danger/20 hover:bg-devsweep-danger/20',
      success: 'bg-devsweep-success/10 text-devsweep-success border border-devsweep-success/20 hover:bg-devsweep-success/20',
      outline: 'bg-transparent text-devsweep-text border border-devsweep-border hover:bg-devsweep-bgTertiary',
    };

    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
      xl: 'px-8 py-4 text-lg',
    };

    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center font-medium rounded-lg transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent focus-visible:ring-offset-2 focus-visible:ring-offset-devsweep-bg',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && 'w-full',
          className
        )}
        disabled={isDisabled}
        {...props}
      >
        {loading ? (
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : icon && iconPosition === 'left' ? (
          <span className="mr-2" aria-hidden="true">{icon}</span>
        ) : null}
        {children}
        {icon && iconPosition === 'right' && <span className="ml-2" aria-hidden="true">{icon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
