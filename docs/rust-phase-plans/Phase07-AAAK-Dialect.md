# Phase 7 Plan: AAAK Dialect

## Objective

Preserve AAAK shorthand rendering, deterministic formatting, and token-efficiency behavior in Rust.

## Dependencies

- Phase 0 AAAK goldens are stable.
- Phase 5 wake-up generation is available.

## Implementation Workstreams

### 1. AAAK Rendering Rules

- Port formatting rules from Python.
- Make output deterministic and free from incidental ordering drift.

### 2. Wake-Up AAAK Output

- Integrate AAAK rendering into wake-up generation.
- Preserve the expected compactness and structural cues.

### 3. Reverse Parsing Scope Decision

- Decide whether reverse parsing is in scope for v1.
- If not, document the deferral clearly so the absence is not accidental.

### 4. Token Efficiency Validation

- Measure and guard token-budget behavior on fixture outputs.
- Keep long-input handling safe and deterministic.

## Deliverables

- AAAK formatter implementation
- Wake-up AAAK generation support
- Reverse parsing scope decision
- Token-budget validation tests

## To-Do Checklist

- [ ] Port AAAK formatting rules.
- [ ] Define deterministic ordering rules for rendered output.
- [ ] Integrate AAAK rendering into wake-up flow.
- [ ] Decide whether reverse parsing is in scope.
- [ ] Implement reverse parsing if retained.
- [ ] Document deferment if reverse parsing is not retained.
- [ ] Add AAAK golden tests.
- [ ] Add formatting invariant tests.
- [ ] Add token-budget tests.
- [ ] Add long-input tests.
- [ ] Add deterministic rendering tests across repeated runs.

## Exit Gates

- AAAK snapshots are stable.
- Token-budget checks pass.
- Reverse parsing is either implemented or explicitly out of scope.

## Risks To Watch

- Quiet formatting drift from map iteration or unstable ordering.
- Treating AAAK only as string formatting instead of a product contract.
- Shipping wake-up output without measuring compactness budgets.
