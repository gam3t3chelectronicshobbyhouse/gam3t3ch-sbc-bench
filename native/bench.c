#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include "suite.h"
#ifdef _WIN32
#include <windows.h>
static double now(void) { LARGE_INTEGER f,t; QueryPerformanceFrequency(&f); QueryPerformanceCounter(&t); return (double)t.QuadPart/f.QuadPart; }
#else
#include <time.h>
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+t.tv_nsec*1e-9; }
#endif
static volatile uint64_t sink;
static void metric(const char *name, double start, double work, const char *unit, int comma) {
    double elapsed=now()-start;
    printf("%s\"%s\":{\"seconds\":%.9f,\"value\":%.6f,\"unit\":\"%s\"}",comma?",":"",name,elapsed,work/elapsed,unit);
    fflush(stdout);
}
static int cpu(void) {
    uint32_t x=0x12345678u, h=2166136261u; unsigned i,j,k,r;
    double t,y=0.125,a[32][32],b[32][32],c[32][32];
    unsigned char input[65536], packed[131072], output[65536]; size_t p,q;
    printf("{"); t=now();
    for(i=0;i<384000000;i++) { x^=x<<13; x^=x>>17; x^=x<<5; }
    sink=x; metric("integer",t,384000000,"iterations/s",0);
    t=now();
    for(i=0;i<256000000;i++) y=y*0.9999997+0.0000002;
    sink=(uint64_t)(y*1e12); metric("floating_point",t,256000000,"iterations/s",1);
    for(i=0;i<65536;i++) input[i]=(unsigned char)((i/16)%251);
    t=now();
    for(r=0;r<16384;r++) for(i=0;i<65536;i++) h=(h^input[i])*16777619u;
    sink=h; metric("hash_fnv1a",t,16384.0*65536/1e6,"MB/s",1);
    t=now();
    for(r=0;r<8192;r++) {
        p=0;
        for(i=0;i<65536;) { unsigned n=1; while(i+n<65536 && n<255 && input[i+n]==input[i]) n++; packed[p++]=(unsigned char)n; packed[p++]=input[i]; i+=n; }
        q=0; for(i=0;i<p;i+=2) for(j=0;j<packed[i];j++) output[q++]=packed[i+1];
        if(q!=sizeof input || memcmp(input,output,sizeof input)) return 2;
        sink+=output[r%65536];
    }
    metric("rle_roundtrip",t,8192.0*65536/1e6,"MB/s",1);
    for(i=0;i<32;i++) for(j=0;j<32;j++) { a[i][j]=(i+j+1)/64.0; b[i][j]=(i==j)?1.0:0.01; }
    t=now();
    for(r=0;r<8192;r++) { a[r%32][r%32]+=0.000001; for(i=0;i<32;i++) for(j=0;j<32;j++) { double s=0; for(k=0;k<32;k++) s+=a[i][k]*b[k][j]; c[i][j]=s; } sink+=(uint64_t)(c[r%32][(r/32)%32]*1e6); }
    metric("matrix",t,8192.0*32*32*32*2/1e6,"MFLOP/s",1);
    printf(",\"checksum\":%llu}",(unsigned long long)sink); return 0;
}
static int memory(void) {
    const size_t n=32u*1024u*1024u; const unsigned passes=32;
    volatile unsigned char *a=(volatile unsigned char*)malloc(n), *b=(volatile unsigned char*)malloc(n);
    size_t i; unsigned r; uint64_t sum=0; double t;
    if(!a||!b) { free((void*)a); free((void*)b); return 3; }
    for(i=0;i<n;i++) { a[i]=(unsigned char)i; b[i]=0; }
    printf("{"); t=now();
    for(r=0;r<passes;r++) for(i=0;i<n;i++) b[i]=a[i];
    metric("copy",t,(double)n*passes/1e6,"MB/s",0);
    t=now(); for(r=0;r<passes;r++) for(i=0;i<n;i++) sum+=a[i];
    sink=sum; metric("read",t,(double)n*passes/1e6,"MB/s",1);
    t=now(); for(r=0;r<passes;r++) for(i=0;i<n;i++) b[i]=(unsigned char)(i+r);
    sink+=b[n-1]; metric("write",t,(double)n*passes/1e6,"MB/s",1);
    printf(",\"buffer_bytes\":%lu,\"passes\":%u,\"checksum\":%llu}",(unsigned long)n,passes,(unsigned long long)sink);
    free((void*)a); free((void*)b); return 0;
}
int main(int argc,char **argv) {
    if(argc!=2) { fprintf(stderr,"usage: g3bench-native cpu|memory|info\n"); return 1; }
    if(!strcmp(argv[1],"cpu")) return cpu();
    if(!strcmp(argv[1],"memory")) return memory();
    if(!strcmp(argv[1],"info")) {
#ifdef __VERSION__
        printf("{\"suite_version\":\"" G3_SUITE_VERSION "\",\"workload_id\":\"" G3_WORKLOAD_ID "\",\"compiler\":\"%s\",\"pointer_bits\":%u}",__VERSION__,(unsigned)(sizeof(void*)*8));
#else
        printf("{\"suite_version\":\"" G3_SUITE_VERSION "\",\"workload_id\":\"" G3_WORKLOAD_ID "\",\"compiler\":\"MSVC\",\"pointer_bits\":%u}",(unsigned)(sizeof(void*)*8));
#endif
        return 0;
    }
    return 1;
}
