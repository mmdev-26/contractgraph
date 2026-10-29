# ContractGraph — design and limitations

## Analysis model

Compatibility is directional: existing requests must remain accepted; new responses must remain acceptable to old consumers. The checker traverses schema properties and array items, resolves local component schema references, compares required fields, enums, types and numeric/length/cardinality bounds, and emits findings tied to operation and field paths. Changes in unsupported constraints, recursive schema pairs, composition, authorization or referenced parameter/body/response objects require manual review.

Declared consumer dependencies form a reverse adjacency graph. A breadth-first search starts at consumers of changed operations; each impacted consumer records a shortest discovered dependency chain. A visited set makes cycles terminate. The SHA-256 input fingerprint binds a report to the exact analyzed scenario.

This is conservative checking, not full OpenAPI conformance. It can over-report incompatibility (for example numeric type widening) and cannot prove safety for arbitrary schemas. External references are rejected. It does not discover consumers from traffic or source code.

## Included scenario

A billing API starts requiring an amount and adds a response enum value. The report identifies two breaking changes and the path from billing-sdk to checkout. The unconnected admin consumer is unaffected.

## Next validation work

Expand JSON Schema dialect coverage, versioned fixtures against established compatibility tools, source-code consumer discovery and large-schema benchmarks. These are roadmap items, not implemented features.

## Public-demo boundary

The hosted workbench is served over HTTPS behind nginx. User scenarios are processed on the server, not in the visitor browser. Input is capped at 512 KB, analysis runs in a separate process with a 3-second CPU limit, a 5-second wall deadline and a 256 MB address-space limit on Linux. At most two analysis workers run per service. The reverse proxy rate-limits analysis and disables request/response buffering to disk. The service runs as a dynamic unprivileged user with a read-only filesystem, private temporary directory and localhost-only network access. These are resource and isolation boundaries, not a claim of a completed security audit.

The UI adds a live evidence visualization and domain-specific quick controls. JSON remains available for full reproducibility. No submitted inputs are intentionally persisted. Public demos are for synthetic data only.
