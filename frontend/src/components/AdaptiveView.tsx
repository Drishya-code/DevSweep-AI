import { ReactNode } from 'react';
import { useViewMode } from '../context/ViewModeContext';

export interface AdaptiveViewProps {
  children?: ReactNode;
  simple?: ReactNode;
  technical?: ReactNode;
}

/**
 * Renders different content based on the current view mode.
 * Exactly one of `simple` or `technical` should be provided, or use `children` as fallback.
 */
export function AdaptiveView({ children, simple, technical }: AdaptiveViewProps) {
  const { viewMode } = useViewMode();

  if (viewMode === 'simple' && simple) {
    return <>{simple}</>;
  }
  
  if (viewMode === 'technical' && technical) {
    return <>{technical}</>;
  }

  // Fallback to children if specific view not provided
  return <>{children}</>;
}

/**
 * Conditional rendering for Simple view only
 */
export function SimpleView({ children }: { children: ReactNode }) {
  const { viewMode } = useViewMode();
  return viewMode === 'simple' ? <>{children}</> : null;
}

/**
 * Conditional rendering for Technical view only
 */
export function TechnicalView({ children }: { children: ReactNode }) {
  const { viewMode } = useViewMode();
  return viewMode === 'technical' ? <>{children}</> : null;
}

/**
 * Shows content in both views but with different styling/classes
 */
export interface AdaptiveClassesProps {
  simple?: string;
  technical?: string;
  base?: string;
}

export function useAdaptiveClasses({ simple = '', technical = '', base = '' }: AdaptiveClassesProps): string {
  const { viewMode } = useViewMode();
  return `${base} ${viewMode === 'simple' ? simple : technical}`.trim();
}