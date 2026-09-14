# Final matched benchmarks — 14 September 2026

The public fork measured **14.04–14.17 tok/s** with two SSD enclosures, against **10.01–10.12 tok/s** for the pinned upstream engine on internal storage: **40.1% faster between medians**.

| Configuration | Run 1 | Run 2 | Confirmation | Median tok/s | Gain |
|---|---:|---:|---:|---:|---:|
| Upstream — internal | 10.12 | 10.01 | — | 10.07 | Baseline |
| Fork — internal | 12.36 | 12.28 | — | 12.32 | +22.4% |
| Fork — internal + one enclosure | 13.14 | 13.46 | 13.65 | 13.46 | +33.7% |
| Fork — internal + two enclosures | 14.04 | 14.17 | — | 14.11 | +40.1% |

Medians are displayed to two decimals; gains use unrounded medians. Rates include the first decode step and exclude prefill and startup.

## Conditions

- M5 Max, 128 GiB; macOS 26.6.2; Apple clang 21 with the macOS 26.5 SDK.
- DeepSeek V4.1 Flash Q4, same full model and prompt files; 512 prompt tokens, 512 generated tokens, context allocation 4096, raw completion mode.
- Fork source: `49cfecc22a93529db0d0ce2a92d07e20fa19d46c`. Upstream: `bd66c402070042bf0a79ad6ece8242de4c93680c`, with only frontend phase markers added; its engine and shaders are unchanged.
- The public fresh-clone binaries and source hashes matched their validated build identities before and after the campaign.
- Automatic cache allocation matched: 68.37 GiB dynamic expert cache and 14.24 GiB prefill reserve. Every arm started a fresh engine; the OS page cache was not purged.
- Dashboard collection, physical-device sampling and optional byte-accounting instrumentation were off. The lightweight swap guard and phase markers were enabled consistently.
- Full, identical GGUF replicas; expert-read weights 2:1 or 2:1:1 for the multi-drive configurations. Engram stayed on internal storage, with eight row readers in the fork.
- Order: upstream, fork internal, fork +1, fork +2; then the reverse. The one-enclosure pair differed by 2.4%, so it received one additional run. All observations are included.

## Validation and scope

All nine generated outputs were byte-identical to upstream and the archived reference. No arm increased swap usage. The three-drive pair differed by 0.92%; the one-enclosure configuration varied 3.79% across its three runs.

This measures one performance prompt on one machine. It does not establish performance on every workload or compare against upstream with multiple drives. The earlier bounded correctness and first-content timing checks are documented in [validation notes](VALIDATION-2026-09-14.md). Physical-byte attribution remains unresolved and was not measured in this throughput campaign; no exact device-byte explanation is claimed.

## Reproduce

Use the [build and run recipe](../reproduce/README.md) with `--prompt-tokens 512 --tokens 512`, the pinned compiler, and the four configurations above. Omit `--sampler` and `--accounting` to match this campaign. Run in forward and reverse order, compare generated output bytes, and retain each measurement.

[Machine-readable results, hashes and per-run measurements](final-matched-2026-09-14.json) · [Chart generator](charts/generate-final.py)
