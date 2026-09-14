#define _DARWIN_C_SOURCE
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static int inject_eintr,delay_reads,active_reads,peak_reads;
static ssize_t observed_pread(int fd,void *dst,size_t n,off_t off){
 int a=__atomic_add_fetch(&active_reads,1,__ATOMIC_SEQ_CST),p=__atomic_load_n(&peak_reads,__ATOMIC_SEQ_CST);
 while(a>p&&!__atomic_compare_exchange_n(&peak_reads,&p,a,0,__ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST)){}
 if(delay_reads)usleep(300);
 ssize_t result;
 if(__atomic_exchange_n(&inject_eintr,0,__ATOMIC_SEQ_CST)){errno=EINTR;result=-1;}
 else result=pread(fd,dst,n,off);
 __atomic_sub_fetch(&active_reads,1,__ATOMIC_SEQ_CST);return result;
}
#define pread observed_pread
#include <ds4_engram.c>
#undef pread
int main(void){
 char path[]="/tmp/ar-engram-par-XXXXXX";int fd=mkstemp(path);assert(fd>=0);
 enum{N=64,COUNT=48};uint8_t raw[N][DS4_ENGRAM_ROW_BYTES];
 for(unsigned r=0;r<N;r++){
  for(unsigned j=0;j<DS4_ENGRAM_DIM;j++){unsigned c=(j+r*7)%256;raw[r][j]=(c&127)==127?0:c;}
  for(unsigned j=DS4_ENGRAM_DIM;j<DS4_ENGRAM_ROW_BYTES;j++)raw[r][j]=117+(r+j)%20;
 }
 assert(write(fd,raw,sizeof(raw))==sizeof(raw));
 setenv("DS4_ARGODRIVE_ACCOUNTING","1",1);
 ds4_engram_table t;assert(ds4_engram_table_open(&t,path,0,N));unlink(path);
 uint32_t ids[COUNT];for(unsigned i=0;i<COUNT;i++)ids[i]=(i*37)%N;
 ids[7]=ids[3];ids[25]=ids[3];
 float reference[COUNT*DS4_ENGRAM_DIM],got[COUNT*DS4_ENGRAM_DIM+8];
 uint64_t before=ar_engram_bytes_snapshot();
 assert(ds4_engram_read(&t,ids,COUNT,reference));
 assert(ar_engram_bytes_snapshot()-before==COUNT*DS4_ENGRAM_ROW_BYTES);
 unsigned counts[]={0,1,7,24,48},readers[]={1,2,4,8,16};
 for(unsigned c=0;c<5;c++)for(unsigned r=0;r<5;r++){
  memset(got,0xa5,sizeof(got));inject_eintr=1;
  assert(ds4_engram_read_parallel(&t,ids,counts[c],got,readers[r]));assert(!active_reads);
  assert(!memcmp(got,reference,counts[c]*DS4_ENGRAM_DIM*4));
  for(size_t z=counts[c]*DS4_ENGRAM_DIM*4;z<sizeof(got);z++)assert(((uint8_t*)got)[z]==0xa5);
 }
 delay_reads=1;peak_reads=0;
 assert(ds4_engram_read_parallel(&t,ids,COUNT,got,8));assert(peak_reads>1&&peak_reads<=8&&!active_reads);
 // A genuine truncated row while other workers remain delayed. Failure returns
 // only when all writers have joined, so caller can release its output at once.
 assert(ftruncate(fd,20*DS4_ENGRAM_ROW_BYTES+17)==0);errno=0;
 assert(!ds4_engram_read_parallel(&t,ids,COUNT,got,8)&&errno==EIO&&!active_reads);
 assert(pwrite(fd,raw,sizeof(raw),0)==sizeof(raw));
 assert(ds4_engram_read_parallel(&t,ids,COUNT,got,8));assert(!memcmp(got,reference,sizeof(reference)));
 uint32_t invalid=64;memset(got,0xa5,sizeof(got));
 assert(!ds4_engram_read_parallel(&t,&invalid,1,got,8)&&errno==EINVAL);
 for(size_t z=0;z<sizeof(got);z++)assert(((uint8_t*)got)[z]==0xa5);
 assert(!ds4_engram_read_parallel(&t,ids,COUNT,got,0)&&errno==EINVAL);
 assert(!ds4_engram_read_parallel(&t,ids,COUNT,got,17)&&errno==EINVAL);
 assert(!ds4_engram_read_parallel(&t,ids,SIZE_MAX,got,8)&&errno==EINVAL);
 // Invalid scalar encoding propagates the decoder's error through worker join.
 uint8_t bad=127;assert(pwrite(fd,&bad,1,(off_t)ids[3]*DS4_ENGRAM_ROW_BYTES)==1);
 assert(!ds4_engram_read_parallel(&t,ids,COUNT,got,8)&&errno==EDOM&&!active_reads);
 ds4_engram_table_close(&t);close(fd);
 puts("PASS Engram parallel: exact values/order, duplicates,1/2/4/8/16 readers, real concurrency, EINTR, EOF, recovery, invalid scalar/index/count, joined writers and canaries");return 0;
}
