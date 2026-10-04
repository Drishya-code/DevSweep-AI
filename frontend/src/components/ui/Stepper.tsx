import { cn } from '../../utils/helpers';

export interface Step {
  id: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface StepperProps {
  steps: Step[];
  currentStep: string;
  onStepClick?: (stepId: string) => void;
  variant?: 'horizontal' | 'vertical';
  className?: string;
  showDescriptions?: boolean;
}

export function Stepper({
  steps,
  currentStep,
  onStepClick,
  variant = 'horizontal',
  className,
  showDescriptions = true,
}: StepperProps) {
  const currentIndex = steps.findIndex(s => s.id === currentStep);
  const completedSteps = new Set(steps.slice(0, currentIndex).map(s => s.id));

  if (variant === 'vertical') {
    return (
      <div className={cn('flex flex-col gap-6', className)} role="navigation" aria-label="Progress steps">
        {steps.map((step, index) => {
          const isCurrent = step.id === currentStep;
          const isCompleted = completedSteps.has(step.id);
          const isDisabled = step.disabled;

          return (
            <div key={step.id} className="flex gap-4">
              <div className="flex flex-col items-center flex-shrink-0">
                <div
                  className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-fast',
                    isCompleted
                      ? 'bg-devsweep-success text-devsweep-bg'
                      : isCurrent
                      ? 'bg-devsweep-accent text-devsweep-bg'
                      : 'bg-devsweep-bgTertiary text-devsweep-textMuted border border-devsweep-border'
                  )}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {isCompleted ? (
                    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : step.icon ? (
                    <span aria-hidden="true">{step.icon}</span>
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={cn(
                      'w-1 h-12 mt-1',
                      isCompleted ? 'bg-devsweep-success' : 'bg-devsweep-border'
                    )}
                    aria-hidden="true"
                  />
                )}
              </div>
              <div className="flex-1 min-w-0 pt-1">
                <button
                  type="button"
                  onClick={() => !isDisabled && onStepClick?.(step.id)}
                  disabled={isDisabled}
                  className={cn(
                    'w-full text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent focus-visible:ring-offset-2 focus-visible:ring-offset-devsweep-bg',
                    isCurrent ? 'text-devsweep-accent' : 'text-devsweep-textSecondary hover:text-devsweep-text'
                  )}
                  aria-disabled={isDisabled}
                >
                  <span className={cn('font-medium', isCurrent && 'font-semibold')}>
                    {step.label}
                  </span>
                  {showDescriptions && step.description && (
                    <p className="text-xs text-devsweep-textMuted mt-0.5">{step.description}</p>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // Horizontal variant
  return (
    <div className={cn('w-full', className)} role="navigation" aria-label="Progress steps">
      <div className="relative">
        {/* Connecting line */}
        <div
          className="absolute top-4 left-0 right-0 h-1 bg-devsweep-border z-0"
          aria-hidden="true"
        />
        <div
          className="absolute top-4 left-0 h-1 bg-devsweep-accent z-1 transition-all duration-normal"
          style={{ width: `${((currentIndex + 1) / steps.length) * 100}%` }}
          aria-hidden="true"
        />
      </div>
      <div className="relative flex items-start justify-between z-10">
        {steps.map((step, index) => {
          const isCurrent = step.id === currentStep;
          const isCompleted = completedSteps.has(step.id);
          const isDisabled = step.disabled;

          return (
            <div key={step.id} className="flex min-w-0 flex-col items-center flex-1 basis-0">
              <button
                type="button"
                onClick={() => !isDisabled && onStepClick?.(step.id)}
                disabled={isDisabled}
                className={cn(
                  'relative w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-fast',
                  'focus:outline-none focus:ring-2 focus:ring-devsweep-accent focus:ring-offset-2 focus:ring-offset-devsweep-bg',
                  isCompleted
                    ? 'bg-devsweep-success text-devsweep-bg'
                    : isCurrent
                    ? 'bg-devsweep-accent text-devsweep-bg ring-4 ring-devsweep-accent/20'
                    : 'bg-devsweep-bgTertiary text-devsweep-textMuted border-2 border-devsweep-border'
                )}
                aria-current={isCurrent ? 'step' : undefined}
                aria-disabled={isDisabled}
                aria-label={`Step ${index + 1}: ${step.label}`}
              >
                {isCompleted ? (
                  <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : step.icon ? (
                  <span aria-hidden="true">{step.icon}</span>
                ) : (
                  <span>{index + 1}</span>
                )}
              </button>
              <div className="mt-3 min-w-0 text-center w-full px-1 sm:px-2">
                <p className={cn(
                  'font-medium text-xs sm:text-sm truncate',
                  isCurrent ? 'text-devsweep-accent' : 'text-devsweep-textSecondary'
                )}>
                  {step.label}
                </p>
                {showDescriptions && step.description && (
                  <p className="hidden sm:block text-xs text-devsweep-textMuted mt-1 truncate">{step.description}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Simple step indicator (just dots/numbers)
export interface SimpleStepperProps {
  steps: Step[];
  currentStep: string;
  className?: string;
}

export function SimpleStepper({ steps, currentStep, className }: SimpleStepperProps) {
  const currentIndex = steps.findIndex(s => s.id === currentStep);
  const completedSteps = new Set(steps.slice(0, currentIndex).map(s => s.id));

  return (
    <div className={cn('flex items-center gap-2', className)} role="navigation" aria-label="Progress steps">
      {steps.map((step, index) => {
        const isCurrent = step.id === currentStep;
        const isCompleted = completedSteps.has(step.id);

        return (
          <div key={step.id} className="flex items-center gap-2">
            <div
              className={cn(
                'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-fast',
                isCompleted
                  ? 'bg-devsweep-success text-devsweep-bg'
                  : isCurrent
                  ? 'bg-devsweep-accent text-devsweep-bg'
                  : 'bg-devsweep-bgTertiary text-devsweep-textMuted border border-devsweep-border'
              )}
              aria-current={isCurrent ? 'step' : undefined}
            >
              {isCompleted ? (
                <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              ) : (
                <span>{index + 1}</span>
              )}
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  'w-8 h-1',
                  isCompleted ? 'bg-devsweep-success' : 'bg-devsweep-border'
                )}
                aria-hidden="true"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
