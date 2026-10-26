import { useContext } from 'react'
import { AppContext } from '../lib/appContext'
export function useAppState() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('PricePilot requires AppProvider')
  return ctx
}
