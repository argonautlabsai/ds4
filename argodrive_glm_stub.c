/* Optional Argodrive hook defaults. The normal ds4 build has no network or
 * external-storage dependency; an integration may replace these weak symbols
 * with a provider at link time. Returning zero always selects the local path. */
#include <stdint.h>

__attribute__((weak)) int argodrive_glm_read(int model_fd, uint64_t offset,
                                             uint64_t len, void *dst) {
    (void)model_fd; (void)offset; (void)len; (void)dst;
    return 0;
}

__attribute__((weak)) void argodrive_glm_mark(uint32_t phase, uint32_t step) {
    (void)phase; (void)step;
}

__attribute__((weak)) void argodrive_glm_set_kind(uint32_t kind) {
    (void)kind;
}
