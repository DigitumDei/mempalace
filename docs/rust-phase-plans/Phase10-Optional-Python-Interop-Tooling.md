# Phase 10 Plan: Optional Python Interop Tooling

## Objective

Support inspection and optional import of Python-era MemPalace state without making Python-user migration a hidden release requirement.

## Dependencies

- Phase 2 storage layer is stable.
- Phase 9 CLI can expose inspection and import commands if this work remains in scope.
- Phase 0 has identified all Python-era persisted artifacts that matter.

## Implementation Workstreams

### 1. Scope Lock

- Decide whether interop ships in the first Rust release.
- If yes, declare artifact coverage explicitly.
- If no, remove any implied promise from release docs and task tracking.

### 2. Legacy State Inspection

- Implement tooling to inspect existing Python-era state without mutating it.
- Cover Chroma state, config files, registry files, and graph files called out in the task plan.

### 3. Dry-Run Reporting

- Implement dry-run analysis that reports what can be imported, what will be rebuilt, and what is incompatible.

### 4. Conversion and Resume

- Implement Chroma-to-LanceDB conversion and related metadata mapping.
- Implement resumable import runs with verification reporting.

## Deliverables

- Interop scope decision
- Legacy inspection tooling
- Dry-run import reporting
- Conversion and resume support if shipped
- Post-import verification reporting

## To-Do Checklist

- [ ] Decide whether Python interop ships in release 1.
- [ ] Document interop scope clearly.
- [ ] Implement legacy state inspection.
- [ ] Inspect legacy Chroma records.
- [ ] Inspect legacy `config.json`.
- [ ] Inspect legacy `people_map.json`.
- [ ] Inspect legacy `entity_registry.json`.
- [ ] Inspect onboarding-generated markdown artifacts.
- [ ] Inspect legacy `knowledge_graph.sqlite3`.
- [ ] Inspect project-local `mempalace.yaml`.
- [ ] Implement dry-run import report.
- [ ] Define metadata remapping rules.
- [ ] Implement Chroma-to-LanceDB conversion if import is shipped.
- [ ] Implement resumable import runs if import is shipped.
- [ ] Implement post-import verification report if import is shipped.
- [ ] Add import fixture tests.
- [ ] Add interrupted import resume tests.
- [ ] Add data-count parity tests.
- [ ] Add metadata parity tests.
- [ ] Add non-Chroma state coverage tests.
- [ ] Add project-local config inspection or import tests.
- [ ] Add compressed-drawer interop tests if compressed storage ships.

## Exit Gates

- Interop is either complete for all declared artifacts or explicitly removed from release scope.
- Dry-run reporting is accurate and actionable.
- Import verification exists if import remains a shipped feature.

## Risks To Watch

- Shipping partial interop while documentation implies full migration coverage.
- Treating legacy file handling as a best-effort feature without explicit artifact coverage.
- Underestimating the maintenance cost of pinned Python compatibility tooling.
