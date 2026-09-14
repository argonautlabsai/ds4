# Credits

The inference engine, tokenizer, model support, Metal kernels and benchmark frontend originate in Salvatore Sanfilippo (antirez) and the ds4 contributors' work. The upstream license is preserved in LICENSE and licenses/.

Argonaut Labs adds experimental weighted expert replica reads, an independent primary expert descriptor policy, earlier expert loading, bounded layer queueing, resident gate/up scheduling, parallel whole-row Engram reads and diagnostic/reproduction tooling. The implementation in this branch is present in source, with no private provider dependency.

Development and review used Claude, ChatGPT and OpenAI Codex. Private chat histories are not included in this repository. Benchmark measurements and validation evidence, rather than authorship tools, determine the scope of the claims.
