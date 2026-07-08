import { createContext, useContext, useState, type ReactNode } from 'react';

interface HistoryState {
  categoryFilter: string | undefined;
  setCategoryFilter: (filter: string | undefined) => void;
  searchText: string;
  setSearchText: (text: string) => void;
}

const HistoryContext = createContext<HistoryState | null>(null);

export function HistoryProvider({ children }: { children: ReactNode }) {
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [searchText, setSearchText] = useState('');

  return (
    <HistoryContext.Provider value={{
      categoryFilter,
      setCategoryFilter,
      searchText,
      setSearchText,
    }}>
      {children}
    </HistoryContext.Provider>
  );
}

export function useHistory(): HistoryState {
  const ctx = useContext(HistoryContext);
  if (!ctx) throw new Error('useHistory must be used within HistoryProvider');
  return ctx;
}
