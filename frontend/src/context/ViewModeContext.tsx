import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';

export type ViewMode = 'simple' | 'technical';

interface ViewModeContextType {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  toggleViewMode: () => void;
}

const ViewModeContext = createContext<ViewModeContextType | undefined>(undefined);

const VIEW_MODE_KEY = 'devsweep-view-mode';
const DEFAULT_VIEW_MODE: ViewMode = 'simple';

export function ViewModeProvider({ children }: { children: ReactNode }) {
  const [viewMode, setViewModeState] = useState<ViewMode>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(VIEW_MODE_KEY) as ViewMode | null;
      if (stored === 'simple' || stored === 'technical') {
        return stored;
      }
    }
    return DEFAULT_VIEW_MODE;
  });

  const setViewMode = useCallback((mode: ViewMode) => {
    setViewModeState(mode);
    if (typeof window !== 'undefined') {
      localStorage.setItem(VIEW_MODE_KEY, mode);
    }
  }, []);

  const toggleViewMode = useCallback(() => {
    setViewMode(viewMode === 'simple' ? 'technical' : 'simple');
  }, [viewMode, setViewMode]);

  return (
    <ViewModeContext.Provider value={{ viewMode, setViewMode, toggleViewMode }}>
      {children}
    </ViewModeContext.Provider>
  );
}

export function useViewMode() {
  const context = useContext(ViewModeContext);
  if (!context) {
    throw new Error('useViewMode must be used within a ViewModeProvider');
  }
  return context;
}