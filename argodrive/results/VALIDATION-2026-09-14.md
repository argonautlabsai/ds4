# Earlier validation checks — 14 September 2026

The complete provider is published and freshly cloned successfully. For the final matched throughput comparison, see [final benchmark results](FINAL-MATCHED-2026-09-14.md). The checks below were recorded before that campaign.

| Gate | Result |
|---|---|
| Reproducible source | PASS: real replica reader and scheduling source, fresh clone build, no private provider |
| Bounded quality regression | PASS: code/prose/reasoning/repeat byte-identical to freshly built upstream; malformed HTTP recovery; GCD 49 pairs |
| First-token timing | Captured: client first-content is separate from benchmark first decode evaluation |
| Application byte accounting | PASS: phase deltas match final routed-reader totals; Engram bytes use the same phase basis |
| Physical attribution | OPEN: internal physical reads are 2.65 GB below instrumented application reads in the measured decode window; cause not established |
| Historical 16.3 speed | Not reproduced as a current inclusive result; it was steady decode excluding first evaluation |

Fresh clang21 pp512/tg128: 14.00 tok/s generation-inclusive, 15.45 steady with accounting off; 13.95 inclusive, 15.48 steady with accounting on. Both generated the historical reference text. This single pair does not establish an overhead bound or a portable performance guarantee.

Client first-content timings on a loaded persistent server (seconds):

| Prompt | Upstream | Fork |
|---|---:|---:|
| Code | 11.112 | 8.021 |
| Prose | 12.027 | 6.919 |
| Reasoning | 7.804 | 4.543 |
| Repeated reasoning after invalid request | 7.432 | 4.244 |

These are individual chat requests, not the raw pp512 benchmark. In the raw benchmark, prompt synchronization to first token selection was 32.973 s; model startup and HTTP delivery are excluded.

Phase-aligned decode bytes (decimal GB):

| Source | Routed expert reader | Engram | Physical reads | Physical minus instrumented application |
|---|---:|---:|---:|---:|
| Internal | 23.15826 | 0.00162 | 20.51428 | -2.64560 |
| Enclosure 1 | 10.43753 | 0 | 10.40213 | -0.03540 |
| Enclosure 2 | 10.43753 | 0 | 10.40213 | -0.03540 |

The routed-reader counters exclude mmap-based prefill loads and cache hits. Device counters can include unrelated traffic and storage effects. F_NOCACHE does not itself establish one-to-one physical attribution. The residual is disclosed, not assigned to caching or timing without further evidence.

The frozen 16.31 steady arm measured 14.70 inclusive. Historical pp512/tg512 inclusive was 15.49–15.56 over three runs. Do not present a best steady sample as an inclusive median.

A default clang14 build produced different greedy text and failed ASan runtime initialization. Explicit clang21/macOS26.5 selection restored historical output equality and all three ASan/UBSan fixtures passed. Thirteen Python harness tests passed. CUDA and distributed inference remain unqualified. The broader no-thinking task suite scored 12/18 at 128 tokens; adaptive reasoning/length reruns are not a single uniform 18/18 result.

See `validation-2026-09-14.json` for values, scopes and explicit open gates. No Hacker News post or email was sent by this validation run.
