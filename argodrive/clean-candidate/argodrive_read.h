/* Experimental expert-only replica reader. Callers must verify full replicas
 * before admission; size and inode checks are not content verification. */
#ifndef ARGODRIVE_READ_H
#define ARGODRIVE_READ_H
#include <dispatch/dispatch.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <limits.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

typedef struct { int fd; unsigned weight; uint64_t bytes; } ar_source;
typedef struct { ar_source source[3]; unsigned count; int invalid; int owns_primary; uint64_t size; } ar_reader;
typedef struct { uint64_t offset, length; } ar_piece;

static void ar_close(ar_reader *r) {
    for (unsigned i=0; i<r->count; i++)
        fprintf(stderr,"ds4: Argodrive source[%u] bytes=%llu\n",i,(unsigned long long)__atomic_load_n(&r->source[i].bytes,__ATOMIC_RELAXED));
    for (unsigned i=r->owns_primary?0:1; i<r->count; i++) close(r->source[i].fd);
    memset(r,0,sizeof(*r));
}
static int ar_weight(const char *s, unsigned *w) {
    if (!s || !*s) return 0;
    for (const char *p=s; *p; p++) if (*p<'0' || *p>'9') return 0;
    char *end; unsigned long n=strtoul(s,&end,10);
    if (*end || n<1 || n>100) return 0;
    *w=(unsigned)n; return 1;
}
static int ar_open(ar_reader *r, int primary, const char *paths, const char *weight) {
    ar_close(r);
    const char *uncached_env = getenv("DS4_ARGODRIVE_PRIMARY_NOCACHE");
    const int uncached = uncached_env && strcmp(uncached_env,"0") != 0;
    if ((!paths || !*paths) && !uncached) return 1;
    struct stat st;
    r->invalid=1;
    if (fstat(primary,&st) || !S_ISREG(st.st_mode) || st.st_size<=0) return 0;
    r->size=(uint64_t)st.st_size;
    unsigned w=2;
    if (weight && !ar_weight(weight,&w)) return 0;
    r->source[0]=(ar_source){primary,w,0}; r->count=1;
    if (uncached) {
        // Open an independent expert descriptor. Changing the mmap/Engram
        // descriptor's policy (including through dup) would confound this test.
#if defined(F_GETPATH) && defined(F_NOCACHE)
        char primary_path[4096]; struct stat same;
        if (fcntl(primary,F_GETPATH,primary_path)<0) {ar_close(r);r->invalid=1;return 0;}
        int expert_fd=open(primary_path,O_RDONLY|O_NONBLOCK);
        if (expert_fd<0) {ar_close(r);r->invalid=1;return 0;}
        if (fstat(expert_fd,&same) || same.st_dev!=st.st_dev || same.st_ino!=st.st_ino ||
            same.st_size!=st.st_size || fcntl(expert_fd,F_NOCACHE,1)<0 ||
            fcntl(expert_fd,F_RDAHEAD,0)<0) {
            close(expert_fd);ar_close(r);r->invalid=1;return 0;
        }
        r->source[0].fd=expert_fd;r->owns_primary=1;
        fprintf(stderr,"ds4: Argodrive primary expert descriptor F_NOCACHE=1; mmap/Engram descriptor unchanged\n");
#else
        ar_close(r);r->invalid=1;return 0;
#endif
    }
    if (!paths || !*paths) {r->invalid=0;return 1;}
    /* Strict comma-separated absolute path*integer syntax. */
    char *copy=strdup(paths); if (!copy) {ar_close(r);r->invalid=1;return 0;}
    char *cursor=copy;
    int ok=1;
    while (cursor && *cursor) {
        char *next=strchr(cursor,',');
        if(next) { *next++=0; if(!*next) {ok=0;break;} }
        char *star=strrchr(cursor,'*');
        if(r->count>=3 || !star || cursor[0]!='/' || !ar_weight(star+1,&w)) {ok=0;break;}
        *star=0;
        int fd=open(cursor,O_RDONLY|O_NONBLOCK);
        struct stat replica;
        if(fd<0) {ok=0;break;}
        if(fstat(fd,&replica) || !S_ISREG(replica.st_mode) || replica.st_size!=st.st_size) {close(fd);ok=0;break;}
        for(unsigned i=0;i<r->count;i++) {
            struct stat old;
            if(fstat(r->source[i].fd,&old) || (old.st_dev==replica.st_dev && old.st_ino==replica.st_ino)) ok=0;
        }
        if(!ok) {close(fd);break;}
#ifdef F_NOCACHE
        if(fcntl(fd,F_NOCACHE,1)<0 || fcntl(fd,F_RDAHEAD,0)<0) {close(fd);ok=0;break;}
#endif
        r->source[r->count++]=(ar_source){fd,w,0}; cursor=next;
    }
    free(copy);
    if(!ok || r->count<2) {ar_close(r);r->invalid=1;return 0;}
    r->invalid=0;return 1;
}
static int ar_plan(const ar_reader *r, uint64_t offset, uint64_t length, ar_piece out[3]) {
    if(r->invalid || r->count<1 || r->count>3 || !length || offset>r->size || length>r->size-offset) return 0;
    const uint64_t block=256*1024;
    uint64_t blocks=length/block, counts[3]={0}, remainder[3]={0}, assigned=0;
    unsigned total=0;
    for(unsigned i=0;i<r->count;i++) {if(!r->source[i].weight || r->source[i].weight>100) return 0;total+=r->source[i].weight;}
    for(unsigned i=0;i<r->count;i++) {counts[i]=blocks*r->source[i].weight/total;remainder[i]=blocks*r->source[i].weight%total;assigned+=counts[i];}
    while(assigned<blocks) {
        unsigned best=0;for(unsigned i=1;i<r->count;i++) if(remainder[i]>remainder[best]) best=i;
        counts[best]++;remainder[best]=0;assigned++;
    }
    uint64_t pos=offset;
    for(unsigned i=0;i<r->count;i++) {
        uint64_t n=counts[i]*block+(i==0?length%block:0);
        out[i]=(ar_piece){pos,n};pos+=n;
    }
    return pos-offset==length;
}
static uint64_t ar_exact(int fd,uint64_t offset,uint64_t length,uint8_t *dst) {
    uint64_t n=0;
    while(n<length) {
        size_t want=length-n>SSIZE_MAX?SSIZE_MAX:(size_t)(length-n);
        ssize_t got=pread(fd,dst+n,want,(off_t)(offset+n));
        if(got<0 && errno==EINTR) continue;
        if(got<=0) break;
        n+=(uint64_t)got;
    }
    return n;
}
static int ar_read(ar_reader *r,uint64_t offset,uint64_t length,uint8_t *dst,uint64_t *bytes) {
    *bytes=0;
    ar_piece pieces[3];
    if(!dst || offset>LLONG_MAX || length>LLONG_MAX-offset || !ar_plan(r,offset,length,pieces)) return 0;
    uint64_t counts[3]={0};
    /* Completion barrier owns dst until all disjoint writes finish, including
     * failures. No partial buffer is accepted or retried while writes remain. */
    ar_piece *pp=pieces; uint64_t *cc=counts;
    dispatch_apply(r->count,dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^(size_t i){
        cc[i]=ar_exact(r->source[i].fd,pp[i].offset,pp[i].length,dst+(pp[i].offset-offset));
        __atomic_fetch_add(&r->source[i].bytes,cc[i],__ATOMIC_RELAXED);
    });
    int ok=1;
    for(unsigned i=0;i<r->count;i++) {*bytes+=counts[i];if(counts[i]!=pieces[i].length) ok=0;}
    return ok;
}
#endif
