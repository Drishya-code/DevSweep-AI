import { useState, useRef, useEffect } from 'react';
import { cn } from '../../utils/helpers';
import { ChevronDown, ChevronUp } from 'lucide-react';

export interface ExpandableSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  className?: string;
  titleClassName?: string;
  contentClassName?: string;
  icon?: React.ReactNode;
  onToggle?: (expanded: boolean) => void;
}

export function ExpandableSection({
  title,
  children,
  defaultExpanded = false,
  className,
  titleClassName,
  contentClassName,
  icon,
  onToggle,
}: ExpandableSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [height, setHeight] = useState(0);
  const contentRef = useRef<HTMLDivElement>(null);
  const isMounted = useRef(false);

  useEffect(() => {
    isMounted.current = true;
    if (expanded && contentRef.current) {
      setHeight(contentRef.current.scrollHeight);
    } else {
      setHeight(0);
    }
  }, [expanded]);

  useEffect(() => {
    if (isMounted.current && contentRef.current && expanded) {
      setHeight(contentRef.current.scrollHeight);
    }
  }, [children]);

  const handleToggle = () => {
    const newExpanded = !expanded;
    setExpanded(newExpanded);
    onToggle?.(newExpanded);
  };

  return (
    <div className={cn('border border-devsweep-border rounded-lg overflow-hidden', className)}>
      <button
        type="button"
        onClick={handleToggle}
        className={cn(
          'w-full px-4 py-3 flex items-center justify-between gap-3',
          'bg-devsweep-bgTertiary/50 hover:bg-devsweep-bgHover transition-colors',
          'text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent focus-visible:ring-inset',
          titleClassName
        )}
        aria-expanded={expanded}
        aria-controls={`expandable-content-${title.replace(/\s+/g, '-').toLowerCase()}`}
      >
        <div className="flex items-center gap-3">
          {icon && <span className="text-devsweep-accent" aria-hidden="true">{icon}</span>}
          <span className="font-medium text-devsweep-text">{title}</span>
        </div>
        <span 
          className={cn(
            'flex-shrink-0 transition-transform duration-fast',
            expanded && 'rotate-180'
          )}
          aria-hidden="true"
        >
          {expanded ? <ChevronUp className="w-4 h-4 text-devsweep-textMuted" /> : <ChevronDown className="w-4 h-4 text-devsweep-textMuted" />}
        </span>
      </button>
      <div
        id={`expandable-content-${title.replace(/\s+/g, '-').toLowerCase()}`}
        className="overflow-hidden transition-all duration-normal"
        style={{ maxHeight: expanded ? height : 0 }}
      >
        <div
          ref={contentRef}
          className={cn('px-4 pb-4 pt-2', contentClassName)}
        >
          {children}
        </div>
      </div>
    </div>
  );
}

// Controlled version for forms/wizards
export interface ControlledExpandableSectionProps {
  title: string;
  children: React.ReactNode;
  expanded: boolean;
  onToggle: (expanded: boolean) => void;
  className?: string;
  titleClassName?: string;
  contentClassName?: string;
  icon?: React.ReactNode;
}

export function ControlledExpandableSection({
  title,
  children,
  expanded,
  onToggle,
  className,
  titleClassName,
  contentClassName,
  icon,
}: ControlledExpandableSectionProps) {
  const [height, setHeight] = useState(0);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (expanded && contentRef.current) {
      setHeight(contentRef.current.scrollHeight);
    } else {
      setHeight(0);
    }
  }, [expanded, children]);

  return (
    <div className={cn('border border-devsweep-border rounded-lg overflow-hidden', className)}>
      <button
        type="button"
        onClick={() => onToggle(!expanded)}
        className={cn(
          'w-full px-4 py-3 flex items-center justify-between gap-3',
          'bg-devsweep-bgTertiary/50 hover:bg-devsweep-bgHover transition-colors',
          'text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent focus-visible:ring-inset',
          titleClassName
        )}
        aria-expanded={expanded}
        aria-controls={`expandable-content-${title.replace(/\s+/g, '-').toLowerCase()}`}
      >
        <div className="flex items-center gap-3">
          {icon && <span className="text-devsweep-accent" aria-hidden="true">{icon}</span>}
          <span className="font-medium text-devsweep-text">{title}</span>
        </div>
        <span 
          className={cn(
            'flex-shrink-0 transition-transform duration-fast',
            expanded && 'rotate-180'
          )}
          aria-hidden="true"
        >
          {expanded ? <ChevronUp className="w-4 h-4 text-devsweep-textMuted" /> : <ChevronDown className="w-4 h-4 text-devsweep-textMuted" />}
        </span>
      </button>
      <div
        id={`expandable-content-${title.replace(/\s+/g, '-').toLowerCase()}`}
        className="overflow-hidden transition-all duration-normal"
        style={{ maxHeight: expanded ? height : 0 }}
      >
        <div
          ref={contentRef}
          className={cn('px-4 pb-4 pt-2', contentClassName)}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
