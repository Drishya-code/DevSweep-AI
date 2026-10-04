import { cn } from '../../utils/helpers';
import { getRiskSemantics } from '../../design-tokens';

export interface RiskBadgeProps {
  risk: 'SAFE' | 'CAUTION' | 'DANGEROUS';
  variant?: 'simple' | 'technical' | 'inline';
  showIcon?: boolean;
  showLabel?: boolean;
  className?: string;
  // Technical view only
  scannerRisk?: 'SAFE' | 'CAUTION' | 'DANGEROUS';
  aiRisk?: 'SAFE' | 'CAUTION' | 'DANGEROUS';
  effectiveRisk?: 'SAFE' | 'CAUTION' | 'DANGEROUS';
}

export function RiskBadge({
  risk,
  variant = 'simple',
  showIcon = true,
  showLabel = true,
  className,
  scannerRisk,
  aiRisk,
  effectiveRisk,
}: RiskBadgeProps) {
  const semantics = getRiskSemantics(risk);
  const baseClasses = 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border';

  if (variant === 'technical' && (scannerRisk || aiRisk || effectiveRisk)) {
    return (
      <div className={cn('flex items-center gap-1.5', className)}>
        {/* Effective risk (primary) */}
        <span className={cn(baseClasses, `bg-devsweep-${semantics.color}/10 text-devsweep-${semantics.color} border-devsweep-${semantics.color}/20`)}>
          {showIcon && <span aria-hidden="true">{semantics.icon}</span>}
          {showLabel && <span>{semantics.label}</span>}
        </span>
        
        {/* Risk breakdown */}
        <div className="flex items-center gap-1 text-xs text-devsweep-textMuted">
          {scannerRisk && (
            <>
              <span className="px-1.5 py-0.5 bg-devsweep-bgTertiary rounded">
                Scanner: {getRiskSemantics(scannerRisk).shortLabel}
              </span>
              {aiRisk && aiRisk !== scannerRisk && (
                <span aria-hidden="true">→</span>
              )}
            </>
          )}
          {aiRisk && aiRisk !== scannerRisk && (
            <span className="px-1.5 py-0.5 bg-devsweep-accent/10 text-devsweep-accent rounded">
              AI: {getRiskSemantics(aiRisk).shortLabel}
            </span>
          )}
        </div>
      </div>
    );
  }

  const riskClasses = `bg-devsweep-${semantics.color}/10 text-devsweep-${semantics.color} border-devsweep-${semantics.color}/20`;

  return (
    <span className={cn(baseClasses, riskClasses, className)}>
      {showIcon && <span aria-hidden="true">{semantics.icon}</span>}
      {showLabel && <span>{semantics.label}</span>}
    </span>
  );
}

// Simple view: just the risk badge with tooltip/explanation on hover
export function SimpleRiskBadge({ risk, className, children }: { risk: 'SAFE' | 'CAUTION' | 'DANGEROUS'; className?: string; children?: React.ReactNode }) {
  const semantics = getRiskSemantics(risk);
  
  return (
    <span 
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border',
        `bg-devsweep-${semantics.color}/10 text-devsweep-${semantics.color} border-devsweep-${semantics.color}/20`,
        className
      )}
      title={semantics.description}
    >
      <span aria-hidden="true">{semantics.icon}</span>
      <span>{semantics.label}</span>
      {children}
    </span>
  );
}