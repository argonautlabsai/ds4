# Clean experimental DeepSeek candidate

Base: antirez/ds4 `bd66c402070042bf0a79ad6ece8242de4c93680c`. Apply `candidate.patch` and copy both headers into a fresh checkout, then use the build and run instructions in `../reproduce/README.md`.

Retained: expert replica split reads, separate primary descriptor policy, exact earlier expert loading, bounded layer queueing, resident gate/up work, parallel whole-row Engram reads, and opt-in phase/profiling telemetry. No reserve expansion, predicted prefetch, whole/flat reader, Q8 arithmetic variants, norm fusion or precommit prototypes.

The frozen candidate completed all 30 local benchmark arms with upstream-matching text. At pp512/tg512 the internal + Green + White median was 15.56 generation tok/s, range 15.49–15.56 across three runs, versus 9.49 upstream internal and 12.90 fork internal. Generation includes the first decode step. This does not establish a public record or achieve the 25 tok/s target.

Reader and Engram fixtures passed ASAN/UBSAN; resident masks passed Metal validation. Held-out code/prose/reasoning text matched upstream. One genuine partial-read/EOF fixture failed a streamed request cleanly and recovered both the same and an unrelated prompt on a persistent server. These are bounded checks, not exhaustive lifecycle or model-quality qualification. CUDA inference is untested.

Original qualified ds4-bench SHA-256: `c5b41aedb2bf4cabe2f59717ec58b71388a3f100953dc7e6eb18e46cd1e12f71`. Runtime shader hashes are also recorded in the qualification evidence. This directory is source only; no public fork has been pushed by this campaign.
