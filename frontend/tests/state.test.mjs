import test from 'node:test'
import assert from 'node:assert/strict'
import { initialState, reducer } from '../src/lib/analysisState.ts'
const fit = { recommended_model: 'linear', linear: { a: 500, b: -2 } }
const opt = { optimal_price: 125, optimal_revenue: 31250 }
const populated = { ...initialState, revision: 7, regressionResult: fit, optimizationResult: opt }
test('a dataset replacement removes results and retains original source separately', () => {
 const rows = [{ event_id: 'e1', ticket_price: 100, tickets_sold: 300 }]
 const next = reducer(populated, { type: 'SET_DATASET', payload: { name: 'new.csv', id: null, isSynthetic: false, observations: rows, sourceRows: rows, validation: { price_min: 100, price_max: 150 } } })
 assert.equal(next.regressionResult, null); assert.equal(next.optimizationResult, null)
 assert.equal(next.revision, 8); assert.equal(next.pMin, 100); assert.equal(next.pMax, 150)
 assert.deepEqual(next.originalRows, rows)
})
test('late regression and optimization responses cannot overwrite a newer dataset/configuration', () => {
 assert.equal(reducer(populated, { type: 'SET_REGRESSION', revision: 6, payload: fit }), populated)
 assert.equal(reducer(populated, { type: 'SET_OPTIMIZATION', revision: 6, payload: opt }), populated)
})
test('changing demand model clears an existing optimum and invalidates pending requests', () => {
 const next = reducer(populated, { type: 'SET_SELECTED_MODEL', payload: 'quadratic' })
 assert.equal(next.optimizationResult, null); assert.equal(next.regressionResult, fit)
 assert.equal(next.selectedModel, 'quadratic'); assert.equal(next.revision, 8)
 assert.equal(reducer(next, { type: 'SET_OPTIMIZATION', revision: 7, payload: opt }).optimizationResult, null)
})
test('changing capacity or bounds clears optimum while preserving fit', () => {
 const next = reducer(populated, { type: 'SET_CONFIG', payload: { pMin: 50, pMax: 200, capacity: 100, p0: 100, maxIterations: 50, priceTolerance: 1e-6, derivativeTolerance: 1e-6, priceIncrement: 5 } })
 assert.equal(next.optimizationResult, null); assert.equal(next.regressionResult, fit)
 assert.equal(next.capacity, 100); assert.equal(next.priceIncrement, 5); assert.equal(next.revision, 8)
})
test('accepted results must match the current revision', () => {
 const next = reducer(populated, { type: 'SET_OPTIMIZATION', revision: 7, payload: opt })
 assert.equal(next.optimizationResult, opt)
})
test('reset clears local observations and advances the revision', () => {
 const next = reducer(populated, { type: 'RESET' })
 assert.equal(next.revision, 8); assert.deepEqual(next.observations, []); assert.equal(next.optimizationResult, null)
})
test('changing model or price constraints resets the hypothetical scenario context', () => {
 const withScenarios = { ...populated, scenarioConfig: { currentPrice: 120, baselinePrice: 100, comparisonPrices: [90, 110], demandMultiplier: 1.4 } }
 for (const action of [{ type: 'SET_SELECTED_MODEL', payload: 'quadratic' }, { type: 'SET_CONFIG', payload: { pMin: 130, pMax: 200, capacity: null, p0: null, maxIterations: 50, priceTolerance: 1e-6, derivativeTolerance: 1e-6, priceIncrement: null } }]) {
  const next = reducer(withScenarios, action)
  assert.deepEqual(next.scenarioConfig, { currentPrice: null, baselinePrice: null, comparisonPrices: [], demandMultiplier: 1 })
 }
})
test('scenario changes preserve the fitted model and base recommendation', () => {
 const scenarioConfig = { currentPrice: 100, baselinePrice: 80, comparisonPrices: [90, 120], demandMultiplier: 0.8 }
 const next = reducer(populated, { type: 'SET_SCENARIO_CONFIG', payload: scenarioConfig })
 assert.deepEqual(next.scenarioConfig, scenarioConfig)
 assert.equal(next.optimizationResult, opt); assert.equal(next.regressionResult, fit); assert.equal(next.revision, 7)
})
