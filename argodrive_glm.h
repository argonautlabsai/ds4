#ifndef ARGODRIVE_GLM_ADAPTER_H
#define ARGODRIVE_GLM_ADAPTER_H
#include <stdint.h>
/* Optional Argodrive adapter. The public ds4 build has no transport library
 * linked; an absent weak symbol keeps the normal local read path active. A
 * provider must return 1 only after complete, verified bytes are in dst. */
#if defined(__APPLE__)
#define ARGODRIVE_WEAK_IMPORT __attribute__((weak_import))
#else
#define ARGODRIVE_WEAK_IMPORT
#endif
int argodrive_glm_read(int model_fd, uint64_t offset, uint64_t len, void *dst) ARGODRIVE_WEAK_IMPORT;
/* Optional engine labels for per-request timing; both are no-ops for behaviour. */
void argodrive_glm_mark(uint32_t phase, uint32_t step);    /* 1 = prefill, 2 = decode (step = eval index) */
void argodrive_glm_set_kind(uint32_t kind);                /* 0 = demand, 1 = prefetch, 2 = carried */
#undef ARGODRIVE_WEAK_IMPORT
#endif
