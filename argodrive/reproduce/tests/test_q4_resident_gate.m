/* Include the runtime only in this private fixture to exercise static encoders
 * without adding a test-only exported API to the production engine. */
#include <ds4_metal.m>
#include <assert.h>
static uint32_t rg_rng=8731;
static uint32_t rg_next(void) {rg_rng^=rg_rng<<13;rg_rng^=rg_rng>>17;rg_rng^=rg_rng<<5;return rg_rng;}
static int rg_check(unsigned in,unsigned width) {
 @autoreleasepool {
  if(!ds4_gpu_init())return 0;
  const size_t row=in/256*144,wb=row*width,nb=6*width+8;
  __unsafe_unretained id<MTLBuffer> ga[6],ua[6];
  NSMutableArray *owners=[NSMutableArray array];
  NSUInteger offsets[6]={0};
  for(unsigned i=0;i<12;i++) {
   id<MTLBuffer> buf=[g_device newBufferWithLength:wb options:MTLResourceStorageModeShared];
   if(!buf)return 0;[owners addObject:buf];
   uint8_t *p=buf.contents;for(size_t j=0;j<wb;j++)p[j]=(uint8_t)rg_next();
   for(size_t j=0;j<wb;j+=144){((uint16_t*)(p+j))[0]=0x1800;((uint16_t*)(p+j))[1]=0x1000;}
   if(i<6)ga[i]=buf;else ua[i-6]=buf;
  }
  ds4_gpu_tensor *xt=ds4_gpu_tensor_alloc(in*4),*gt=ds4_gpu_tensor_alloc(nb*4),
      *ut=ds4_gpu_tensor_alloc(nb*4),*mt=ds4_gpu_tensor_alloc(nb*4),*wt=ds4_gpu_tensor_alloc(6*4);
  if(!xt||!gt||!ut||!mt||!wt)return 0;
  float *x=malloc(in*4),weights[6]={.12f,.23f,.16f,.11f,.18f,.20f};
  float *ref[3],*got[3];for(int j=0;j<3;j++){ref[j]=malloc(nb*4);got[j]=malloc(nb*4);}
  for(unsigned i=0;i<in;i++)x[i]=(int32_t)(rg_next()%2001-1000)*0.0001f;
  assert(ds4_gpu_tensor_write(xt,0,x,in*4)&&ds4_gpu_tensor_write(wt,0,weights,24));
  ds4_gpu_mul_mv_id_args args=ds4_gpu_make_mul_mv_id_args(in,width,256,row,wb,1,6,1,
      ds4_gpu_routed_mv_nr0(DS4_METAL_TENSOR_Q4_K));
  args.tp_world=1;
  ds4_gpu_dsv4_moe_swiglu_weight_args act={.width=width,.rows=6,
      .gate_row_stride=width*4,.up_row_stride=width*4,.mid_row_stride=width*4,
      .weight_stride=4,.write_clamped=0,.clamp_value=7.f};
  ds4_gpu_tensor *outputs[3]={gt,ut,mt};
  int ok=1;unsigned masks[]={0,1,3,0x15,0x2a,0x3f,0x40};
  for(unsigned k=0;k<sizeof(masks)/sizeof(*masks)&&ok;k++) {
   for(int j=0;j<3;j++)ok=ok&&ds4_gpu_tensor_fill_f32(outputs[j],NAN,nb);
   for(unsigned pass=0;pass<(k?2:1)&&ok;pass++) {
    uint32_t mask=pass?(0x3fu&~masks[k]):masks[k];
    if(pass&&!mask)continue;
    ok=ds4_gpu_begin_commands();
    if(ok)ok=ds4_gpu_encode_mul_mv_slots6_pair_swiglu(g_batch_cb,
        g_moe_mul_mv_slots6_q4_k_pair_swiglu_pipeline,&args,&act,ga,offsets,ua,offsets,
        ds4_gpu_tensor_buffer(xt),ds4_gpu_tensor_offset(xt),
        ds4_gpu_tensor_buffer(gt),ds4_gpu_tensor_offset(gt),
        ds4_gpu_tensor_buffer(ut),ds4_gpu_tensor_offset(ut),
        ds4_gpu_tensor_buffer(mt),ds4_gpu_tensor_offset(mt),
        ds4_gpu_tensor_buffer(wt),ds4_gpu_tensor_offset(wt),
        ds4_gpu_routed_mv_smem(DS4_METAL_TENSOR_Q4_K),2,false,mask);
    if(!ds4_gpu_end_commands())ok=0;
    for(int j=0;j<3&&ok;j++) {
     ok=ds4_gpu_tensor_read(outputs[j],0,got[j],nb*4);
     if(!k)memcpy(ref[j],got[j],nb*4);
     for(unsigned z=0;z<nb&&ok;z++) {
      int written=z<6*width&&(!k||pass||(masks[k]&(1u<<(z/width))));
      if(written) {
       if(!isfinite(got[j][z])||memcmp(got[j]+z,ref[j]+z,4)) {
        fprintf(stderr,"Q4 mask mismatch in=%u width=%u mask=%x pass=%u tensor=%d index=%u ref=%a got=%a\n",in,width,masks[k],pass,j,z,ref[j][z],got[j][z]);ok=0;
       }
      } else if(!isnan(got[j][z])) {fprintf(stderr,"Q4 mask wrote inactive slot/canary\n");ok=0;}
     }
    }
   }
  }
  for(int j=0;j<3;j++){free(ref[j]);free(got[j]);ds4_gpu_tensor_free(outputs[j]);}
  free(x);ds4_gpu_tensor_free(xt);ds4_gpu_tensor_free(wt);ds4_gpu_cleanup();
  fprintf(stderr,"Q4 resident masks in=%u width=%u: %s\n",in,width,ok?"PASS":"FAIL");return ok;
 }
}
int main(void){return rg_check(256,32)&&rg_check(5120,2048)&&rg_check(8192,256)?0:1;}
