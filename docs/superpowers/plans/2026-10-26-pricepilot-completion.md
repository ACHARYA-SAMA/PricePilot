# PricePilot completion implementation plan

**Goal:** Complete the user-approved seven-phase local application, with executed evidence.

**Architecture:** Preserve FastAPI as the sole numerical engine and React/TypeScript/Vite as the interface. Stateless requests contain active observations and configuration. Exports recompute the same full-data models used by the UI.

**Spec:** User attachment `C:/Users/Arman Acharya/.codex/attachments/2d489011-0852-4a26-83cd-8e50a333950e/Pasted text.txt` and mandatory zero-hallucination policy in chat. User explicitly authorized uninterrupted implementation.

## Constraints and review focus

- No paid services, external AI, fabricated results or unexecuted test claims.
- Verify math before UI integration; distinguish synthetic data from real validation.
- Prevent stale results after dataset/configuration changes.
- Reject nonfinite/fractional/negative counts and ambiguous CSV columns.
- Compare boundaries, stationary roots, capacity breakpoints and optional price increments.
- Exports preserve configuration, provenance and actual warnings.
- No Git repository exists here; preserve existing files without manufacturing history.

## Tasks and verification

1. Numerical engine: baseline pytest, then failing edge cases for regression/full-data refits, Newton residuals, feasibility/capacity. Files: backend/app/core and math tests. Check exact linear reference and quadratic recovery.
2. API/exports: failing integration tests for sample workflow, malformed requests, mapping and full-length exports. Harden schemas; implement consistent export analysis service and PDF with plots/iteration/candidate evidence. Check pytest and rendered PDF.
3. Frontend: wire all nine pages, invalidating state, data editing/grouping/mapping, backend chart data, simulator, diagnostics, KaTeX and active-config exports. Check build/lint/state tests and actual browser flows.
4. Documentation: deterministic CSVs, dictionary, derivations, pseudocode, academic report, 30+ viva answers, presentation outline, five-minute demo and startup guide. Report only executed numerical examples.
5. Integration: start both servers, exercise valid/invalid flows and downloads, inspect desktop/tablet/mobile and PDF. Save commands, exit codes, actual outputs, screenshots and gaps in docs/implementation_audit.md.

## Shared interfaces

- Keep `/api/v1` paths compatible.
- Report/export bodies gain optional model_type,p_min,p_max,capacity,p0,price_increment,dataset_name,is_synthetic.
- CSV validation accepts multipart column_mapping JSON source=>canonical.
- New backend exports: /exports/cleaned-csv and /exports/chart-svg.
- Returned model fits use all data; holdout scores use training-only coefficients.

## Evidence ledger

- Original math suite: worker executed 53 passing tests. No API tests at baseline.
- Original App.tsx was the Vite starter; only two unattached project pages existed.
- Final verification evidence will be recorded after execution in implementation_audit.md.
