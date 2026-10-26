import { createContext, type Dispatch } from 'react'
import type { AnalysisState } from '../types'
import type { Action } from './analysisState'
export const AppContext = createContext<{ state: AnalysisState; dispatch: Dispatch<Action> } | null>(null)
