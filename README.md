# ContractGraph

**Understand the blast radius of an API change.**

Directional OpenAPI schema compatibility and declared consumer dependency analysis.

Original, inspectable Python implementation by mmdev. A scoped research-oriented prototype, not a claim of enterprise maturity, customer adoption or complete standards compliance.

## Quick start

Python 3.11 or newer. No packages, keys or cloud accounts required.

```sh
python3 app.py analyze example.json --output report.json
python3 app.py serve --port 8080
```

Open http://127.0.0.1:8080. Load the included scenario, edit or import JSON, run the analysis, inspect tables and export a report. When run locally, the workbench binds to loopback and processes inputs in your Python process. The hosted demo instead sends your scenario to the AGENCIA server; it does not save submitted input. Do not submit personal, confidential or production data to a public demo. No external AI API calls, telemetry, cookies or input persistence. Maximum request size is 512 KB.

## Tests

```sh
python3 -m unittest discover -v
```

## Architecture

- `engine.py`: deterministic core with `analyze(input)` returning structured evidence.
- `app.py`: CLI plus size-limited, loopback-only JSON workbench server.
- `index.html`: accessible browser interface, evidence tables, metrics and report export.
- `example.json`: synthetic reproducible scenario.
- `test_engine.py`: algorithm invariants, adverse inputs and regression cases.

The engine returns `summary`, domain-specific report sections and explicit `limitations`. It uses no model calls. Input validation is bounded to the supported contract; arbitrary JSON structures are not promised to be meaningful inputs.

## Scope

Read the limitations returned in `report.json`. This version does not connect to live business systems or make external changes. All fixtures are synthetic. Never infer performance or correctness beyond the tested supported cases.

## License

MIT — see LICENSE.

## Design details

See [ARCHITECTURE.md](ARCHITECTURE.md) for the algorithm, guarantees, limitations and roadmap. [example-report.json](example-report.json) is generated from the included fixture.

![Workbench preview](preview.png)

## Live demonstration

https://agencia.sk/labs/contractgraph/

The hosted demo uses two bounded concurrent analysis slots, child-process isolation, CPU/memory deadlines and reverse-proxy rate limits. It is a demonstration service, not a private data-processing environment. The hosted demo runs on Linux.
