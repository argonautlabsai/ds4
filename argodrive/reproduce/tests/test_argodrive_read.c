#include "argodrive_read.h"
#include <assert.h>
#include <pthread.h>
static ar_reader r;
static unsigned char *reference;
static const size_t size=8*1024*1024+123;
static void *reader(void *arg) {
    uintptr_t seed=(uintptr_t)arg;
    unsigned char *dst=malloc(1024*1024+77);assert(dst);
    for(unsigned j=0;j<40;j++) {
        size_t offset=(j*97531+seed*7919)%(size-1024*1024-77),n=1+(j*17777)%(1024*1024);
        uint64_t actual;assert(ar_read(&r,offset,n,dst,&actual));assert(actual==n);assert(!memcmp(dst,reference+offset,n));
    }
    free(dst);return NULL;
}
int main(void) {
    reference=malloc(size);assert(reference);
    for(size_t i=0;i<size;i++)reference[i]=(unsigned char)((i*13+i/4096)%251);
    char dir[]="/tmp/ds41-reader-test-XXXXXX";assert(mkdtemp(dir));
    char path[3][256];int fd[3];
    for(int i=0;i<3;i++){snprintf(path[i],sizeof(path[i]),"%s/source%d",dir,i);fd[i]=open(path[i],O_CREAT|O_EXCL|O_RDWR,0600);assert(fd[i]>=0);assert(write(fd[i],reference,size)==size);}
    char config[600];snprintf(config,sizeof(config),"%s*1,%s*1",path[1],path[2]);assert(ar_open(&r,fd[0],config,"2"));
    ar_piece pieces[3];assert(ar_plan(&r,0,27*256*1024,pieces));assert(pieces[0].length==13*256*1024);assert(pieces[1].length==7*256*1024);assert(pieces[2].length==7*256*1024);
    assert(!ar_plan(&r,size-2,3,pieces));assert(!ar_plan(&r,0,0,pieces));
    pthread_t t[8];for(uintptr_t i=0;i<8;i++)assert(!pthread_create(&t[i],NULL,reader,(void*)i));for(int i=0;i<8;i++)pthread_join(t[i],NULL);
    /* Genuine short read, not a post-hoc flag: truncation in the fixture. */
    assert(!ftruncate(fd[2],0));unsigned char *dst=malloc(size);uint64_t actual;
    assert(!ar_read(&r,0,size,dst,&actual));assert(actual<size);
    ar_close(&r);assert(fcntl(fd[0],F_GETFD)>=0);
    assert(!ar_open(&r,fd[0],config,"2")); /* wrong-size replica rejected */
    snprintf(config,sizeof(config),"%s*1",path[0]);assert(!ar_open(&r,fd[0],config,"2"));
    snprintf(config,sizeof(config),"%s*1",path[1]);assert(!ar_open(&r,fd[0],config,"0"));
    assert(ar_open(&r,fd[0],config,"2"));assert(r.count==2);assert(ar_read(&r,11,1000001,dst,&actual));assert(!memcmp(dst,reference+11,1000001));
    ar_close(&r);assert(ar_open(&r,fd[0],NULL,NULL));assert(!r.count && !r.invalid);
    for(int i=0;i<3;i++){close(fd[i]);unlink(path[i]);}rmdir(dir);free(dst);free(reference);
    puts("PASS: 2/3-source reconstruction, exact coverage, unaligned ranges, 8 concurrent clients, genuine short reads, wrong size/duplicate/weight rejection, primary ownership, disabled state.");
}
