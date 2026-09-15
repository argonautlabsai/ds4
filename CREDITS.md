# Credits

The inference engine, tokenizer, model support, Metal kernels and benchmark frontend originate in Salvatore Sanfilippo (antirez) and the ds4 contributors' work. The upstream license is preserved in LICENSE and licenses/.

Argonaut Labs adds experimental weighted expert replica reads, staged and selective prefill (reading only the experts a chunk's router selected), an independent primary expert descriptor policy, earlier expert loading, bounded layer queueing, resident gate/up scheduling, parallel whole-row Engram reads and diagnostic/reproduction tooling.

One finding here belongs to upstream rather than to this fork: `ds41_graph_prefill_sweep` reads every expert of every routed layer, while a 512-token chunk routes to 187 of 384 per layer, so the sweep reads about twice what the model touches. That is upstream behaviour, measured on the unmodified binary, and the selective read that fixes it needs none of the replica machinery above. It was reported to the author. The implementation in this branch is present in source, with no private provider dependency.

Development and review used Claude, ChatGPT and OpenAI Codex. Private chat histories are not included in this repository. Benchmark measurements and validation evidence, rather than authorship tools, determine the scope of the claims.
