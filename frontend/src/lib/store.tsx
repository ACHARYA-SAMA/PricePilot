import { useReducer, type ReactNode } from 'react'
import { reducer, initialState } from './analysisState'
import { AppContext } from './appContext'
export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  return <AppContext.Provider value={{ state, dispatch }}>{children}</AppContext.Provider>
}
