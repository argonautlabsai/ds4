# Reproduce the DeepSeek V4.1 Flash Q4 experiment

This pack targets macOS Metal on an M5 Max with 128 GiB of unified memory. It contains no model weights or prebuilt engine. Start with the upstream commit recorded below; the Argodrive additions are experimental. They are not the GLM fork's `DS4_MODEL_*` settings.

The full model is **518,596,067,328 bytes**, SHA-256 **a5e2e2c3ada4b2e98d9f9e4b50f6d9c2a12c2c96f5da165c07e13aff9264984e**. Each enclosure needs a full, identical replica. This is application-level split reading, not RAID. Engram rows stay on the primary SSD. Keep other inference, drive calibration and model copying stopped while measuring.

## Build two separate checkouts

On the `argonaut-v41-benchmark` branch, `make -j4 ds4 ds4-bench ds4-server` builds the real reader directly. Paths below are relative to `argodrive/`. The legacy `build.py` recipe rebuilds the frozen source; for new phase accounting use this branch build.

From the pack directory, with Xcode and Python 3 available. Pin the per-shell toolchain first (`export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer`); the frozen campaign used Apple clang 21 and macOS 26.5 SDK. Record `xcrun clang --version` and `xcrun --show-sdk-path`. Older Command Line Tools can produce different greedy output:

```sh
python3 reproduce/build.py --variant upstream --checkout /path/to/upstream
python3 reproduce/build.py --variant fork --checkout /path/to/argodrive-ds4
```

Both checkouts use upstream commit `bd66c402070042bf0a79ad6ece8242de4c93680c`. The upstream benchmark frontend receives only prefill/decode phase markers; its engine and shaders are unchanged. The fork receives `clean-candidate/candidate.patch` and its two headers. Build identities are written into each checkout. Run the binaries from their checkout so runtime Metal sources remain available. Do not run `make cpu` in these directories: it replaces the executable names with CPU builds.

The original campaign used the Xcode clang and macOS 26.5 SDK recorded in the evidence. A new toolchain or checkout path can change the binary hash. New builds need new qualification; the recorded speeds are not guaranteed on every rebuild or Mac.

Run the bounded C reader/Engram fixtures with sanitizers after building, while inference is idle:

```sh
python3 reproduce/test-readers.py --engine-source /path/to/argodrive-ds4
python3 -m unittest discover -s reproduce/tests -p 'test_*.py'
```

The GPU resident-mask fixture source and its recorded Metal-validation log are included separately. The C fixture runner does not claim to run that GPU check.

## Verify existing files once

Replace the example paths with your actual files. `verify.py` reads every file fully; it neither copies nor modifies weights. It refuses to overwrite an existing receipt. The receipt is local to these files and volumes and cannot be reused after a file changes or moves.

```sh
python3 reproduce/verify.py \
  --model /path/to/DeepSeek-V4.1-Flash-Q4.gguf \
  --replica /Volumes/Green/DeepSeek-V4.1-Flash/DeepSeek-V4.1-Flash-Q4.gguf \
  --replica /Volumes/White/DeepSeek-V4.1-Flash/DeepSeek-V4.1-Flash-Q4.gguf \
  --out /path/to/new-receipt.json
```

## Run one arm explicitly

`plan` prints arguments and requested settings without launching inference. `run` checks file receipts, engine/prompt/shader identities, distinct physical SSDs, another-engine exclusion and a 256 MiB swap-growth guard. It clears inherited `DS4_`, `GLM_` and `K3_` variables. Output directories must be new. The scripts never purge the OS page cache or change system power settings.

```sh
python3 reproduce/run.py run --variant fork \
  --engine /path/to/argodrive-ds4/ds4-bench \
  --model /path/to/DeepSeek-V4.1-Flash-Q4.gguf \
  --prompt /path/to/argodrive-ds4/speed-bench/promessi_sposi.txt \
  --replica /Volumes/Green/DeepSeek-V4.1-Flash/DeepSeek-V4.1-Flash-Q4.gguf \
  --replica /Volumes/White/DeepSeek-V4.1-Flash/DeepSeek-V4.1-Flash-Q4.gguf \
  --receipt /path/to/new-receipt.json \
  --prompt-tokens 512 --tokens 512 --out /path/to/new-arm
```

For fork internal-only, omit both `--replica` arguments. For one enclosure, include only the first. For the control use `--variant upstream`, its separate executable and no replicas. All variants retain automatic cache sizing and the same Q4 file, prompt frontier and 4096 context allocation. The benchmark's raw completion mode differs from the separate chat quality tests.

The fork profile enables queueing across layers, earlier loading after the actual router IDs are known, an independent primary expert descriptor with `F_NOCACHE` and read-ahead disabled, resident gate/up work before missing experts arrive, eight whole-row Engram readers and phase markers. Replica weights start at **2:1:1**, with 256 KiB block apportionment. These are measured starting settings for this hardware, not a universal optimizer. Unset experimental flags to disable them; some are presence-based, so setting `0` is not a general off switch.

## Optional physical-device evidence

```sh
xcrun clang -O2 reproduce/phase-sampler.c -o /path/to/phase-sampler \
  -framework CoreFoundation -framework IOKit
```

Add `--sampler /path/to/phase-sampler` to the run command, then:

```sh
python3 reproduce/analyze-phases.py /path/to/new-arm
```

This uses 100 ms cumulative physical read counters and monotonic prefill/decode boundaries. Boundary interpolation includes adjacent-sample bounds. Device traffic can include other processes; application bytes are reported separately over the whole engine arm. Do not divide whole-arm bytes by a decode-only duration.

## Repeat the same matrix

Use three repetitions at each generation length, **128 and 512**, after **512 prompt tokens**. Rotate the four configurations: upstream internal; fork internal; fork + Green; fork + Green + White. Repetition 1 uses that order; repetition 2 reverses both configuration and length order; repetition 3 uses one enclosure, upstream, two enclosures, fork internal. Also run three alternating upstream/two-enclosure pairs with **2048 prompt tokens and 60 generated tokens**.

Compare `generated.txt` byte-for-byte against upstream separately for each prompt/generation length. Report all arms, medians and min–max ranges. `generation_tok_s` includes the first decode step; `steady_tok_s` excludes it. Prompt processing and client-observed first response are separate measurements. The JSON starts with `publication_ready: false`: completing a benchmark is not automatic promotion.

The bundled evidence describes one performance prompt, additional code/prose/reasoning output checks, and a particular persistent-server read-failure recovery test. It does not establish general model quality, every server lifecycle path, another Mac's performance, CUDA support or a public speed record.

## Phase accounting added on this branch

Add `--accounting --sampler /path/to/phase-sampler` for application byte snapshots immediately around prefill and decode. `ARGODRIVE_BYTES` columns are boundary, expert bytes on primary, enclosure 1, enclosure 2, and Engram successful read bytes on primary. Subtract matching boundaries; do not compare final source totals with only decode device traffic. Engram counts include successful partial syscalls if a read fails. Whole-device reads include unrelated processes and storage effects; residuals must be published, not labelled as exact application attribution.

`ARGODRIVE_FIRST_TOKEN_READY` measures the benchmark's first token selection after prefill, with a loaded model. It excludes model startup and HTTP delivery. The CSV's `gen_first_ms` instead measures evaluation of that token. Neither field is client-observed TTFT. Accounting is opt-in and requires an overhead comparison before using that arm's rate as a headline.

If AddressSanitizer fails during runtime initialization before main, preserve that error. `--sanitizers undefined` runs a separately labelled UBSan fixture check; it does not establish an ASan pass.
