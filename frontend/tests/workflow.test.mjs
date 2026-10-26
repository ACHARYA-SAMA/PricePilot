import test from 'node:test'
import assert from 'node:assert/strict'
import { initialState, reducer } from '../src/lib/analysisState.ts'
import { sampleOptimizationParams, optimizationParams } from '../src/services/api.ts'
test('first-time sample optimization uses precisely the configuration installed in the UI', () => {
 const observations = [{ event_id: 'e1', ticket_price: 50, tickets_sold: 400 }, { event_id: 'e2', ticket_price: 150, tickets_sold: 200 }]
 const installed = reducer({ ...initialState, maxIterations: 12, derivativeTolerance: 0.5, capacity: 7, revision: 4 }, {
  type: 'SET_DATASET', payload: { name: 'Synthetic sample', id: 'standard', isSynthetic: true,
   observations, sourceRows: observations, validation: { price_min: 50, price_max: 150 } }
 })
 const actual = sampleOptimizationParams(installed, 'quadratic')
 const expected = optimizationParams({ ...installed, selectedModel: 'quadratic' })
 assert.deepEqual(actual, expected)
 assert.equal(actual.max_iterations, initialState.maxIterations)
 assert.equal(actual.price_tolerance, initialState.priceTolerance)
 assert.equal(actual.derivative_tolerance, initialState.derivativeTolerance)
 assert.equal(actual.capacity, undefined)
 assert.equal(actual.p_min, 50); assert.equal(actual.p_max, 150)
})
import { sourceRowsFromValidation } from '../src/services/api.ts'
test('the imported source order survives accepted and rejected row separation', () => {
 const first = { _source_row: 2, event_id: 'first', ticket_price: 50, tickets_sold: 300 }
 const second = { _source_row: 3, event_id: 'second', ticket_price: 'bad', tickets_sold: 280 }
 const third = { _source_row: 4, event_id: 'third', ticket_price: 100, tickets_sold: 200 }
 const result = sourceRowsFromValidation({ valid_rows_data: [first, third], rejected_rows_data: [second] })
 assert.deepEqual(result, [first, second, third])
})
import { exportPayload } from '../src/services/api.ts'
test('exports preserve the last valid scenario assumptions while keeping base optimization inputs', () => {
 const state = { ...initialState, datasetName: 'Test sample', pMin: 50, pMax: 170, capacity: 250, selectedModel: 'quadratic',
  optimizationResult: { optimal_price: 95.5 },
  scenarioConfig: { currentPrice: 110, baselinePrice: 80, comparisonPrices: [100, 110], demandMultiplier: 1.3 } }
 const payload = exportPayload(state)
 assert.deepEqual(payload.scenario_prices, [110, 100, 80, 95.5])
 assert.equal(payload.baseline_price, 80); assert.equal(payload.demand_multiplier, 1.3)
 assert.equal(payload.model_type, 'quadratic'); assert.equal(payload.capacity, 250)
 assert.equal(payload.p_min, 50); assert.equal(payload.p_max, 170)
 assert.equal(payload.derivative_tolerance, initialState.derivativeTolerance)
})
