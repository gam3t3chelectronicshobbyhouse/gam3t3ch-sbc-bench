#include <SDL.h>
#include <GLES2/gl2.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "suite.h"
static int probing=0;
static int reject(const char *status,const char *message);
static const char *vs="precision mediump float; attribute vec2 position; uniform float phase; uniform float aspect; uniform vec2 offset; uniform float scale; varying vec2 uv; void main(){uv=position; float c=cos(phase),s=sin(phase); vec2 p=mat2(c,-s,s,c)*position; gl_Position=vec4((p*scale+offset)*vec2(1.0/aspect,1.0),0.0,1.0);}";
static const char *fs="precision mediump float; varying vec2 uv; uniform float phase; uniform float light; void main(){float grid=mod(floor(uv.x*6.0)+floor(uv.y*6.0),2.0); float glow=0.5+0.5*sin(phase+uv.x*4.0+uv.y*3.0); vec3 col=mix(vec3(0.04,0.8,0.7),vec3(0.65,0.15,0.95),glow); float lamps=0.0; for(int i=0;i<4;i++){vec2 pos=vec2(sin(float(i)*1.57+phase),cos(float(i)*1.57+phase)); lamps+=0.08/(0.1+length(uv-pos));} gl_FragColor=vec4(col*(0.45+grid*0.35+light*lamps),0.78);}";
static GLuint shader(GLenum kind,const char *source) { GLuint s=glCreateShader(kind); GLint ok; glShaderSource(s,1,&source,NULL); glCompileShader(s); glGetShaderiv(s,GL_COMPILE_STATUS,&ok); if(!ok){char log[2048];glGetShaderInfoLog(s,sizeof log,NULL,log);exit(reject("unsupported",log));}return s; }
static int compare(const void *a,const void *b){double x=*(const double*)a,y=*(const double*)b;return(x>y)-(x<y);}
static void json_string(const char *s){putchar('"');for(;s&&*s;s++){unsigned char c=(unsigned char)*s;if(c=='"'||c=='\\')putchar('\\');if(c>=32)putchar(c);}putchar('"');}
static int reject(const char *status,const char *message){
    fprintf(stderr,"%s\n",message);
    if(probing){printf("{\"suite_version\":\"" G3_SUITE_VERSION "\",\"workload_id\":\"" G3_WORKLOAD_ID "\",\"status\":");json_string(status);printf(",\"reason\":");json_string(message);printf("}");return 0;}
    return 2;
}
int main(int argc,char **argv) {
    int width=1280,height=720,fullscreen=1,counts[]={16,128,128,512,1024},scene;
    SDL_Window *window; SDL_GLContext ctx; GLuint program,buffer; GLint phase,aspect,offset,scale,light,ok;
    const GLfloat vertices[]={-1,-1,1,-1,-1,1,1,1};
    for(int i=1;i<argc;i++){if(!strcmp(argv[i],"--compat")){width=640;height=360;}else if(!strcmp(argv[i],"--fullscreen"))fullscreen=1;else if(!strcmp(argv[i],"--windowed"))fullscreen=0;else if(!strcmp(argv[i],"--probe"))probing=1;else return 1;}
    if(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_TIMER))return reject("unavailable",SDL_GetError());
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2); SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER,1); SDL_GL_SetAttribute(SDL_GL_MULTISAMPLESAMPLES,0);
    SDL_GL_SetAttribute(SDL_GL_RED_SIZE,8); SDL_GL_SetAttribute(SDL_GL_GREEN_SIZE,8); SDL_GL_SetAttribute(SDL_GL_BLUE_SIZE,8); SDL_GL_SetAttribute(SDL_GL_ALPHA_SIZE,8);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE,0); SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE,0);
    window=SDL_CreateWindow("GAM3T3CH 3D Benchmark | GLES 2",SDL_WINDOWPOS_CENTERED,SDL_WINDOWPOS_CENTERED,width,height,SDL_WINDOW_OPENGL|(fullscreen?SDL_WINDOW_FULLSCREEN:0)|(probing?SDL_WINDOW_HIDDEN:SDL_WINDOW_ALWAYS_ON_TOP));
    if(!window)return reject("unavailable",SDL_GetError());
    if(!probing)SDL_RaiseWindow(window);
    ctx=SDL_GL_CreateContext(window); if(!ctx)return reject("unsupported",SDL_GetError());
    if(SDL_GL_SetSwapInterval(0)!=0)return reject("unsupported","Cannot disable vsync; requested graphics test is unsupported in this display configuration.");
    int actual_w,actual_h; SDL_GL_GetDrawableSize(window,&actual_w,&actual_h);
    if(actual_w!=width||actual_h!=height)return reject("unsupported","Requested graphics resolution unavailable; workload resolution is not reduced automatically.");
    program=glCreateProgram(); glAttachShader(program,shader(GL_VERTEX_SHADER,vs)); glAttachShader(program,shader(GL_FRAGMENT_SHADER,fs)); glBindAttribLocation(program,0,"position"); glLinkProgram(program);glGetProgramiv(program,GL_LINK_STATUS,&ok);if(!ok){char log[4096];glGetProgramInfoLog(program,sizeof log,NULL,log);return reject("unsupported",log);}glUseProgram(program);
    phase=glGetUniformLocation(program,"phase");aspect=glGetUniformLocation(program,"aspect");offset=glGetUniformLocation(program,"offset");scale=glGetUniformLocation(program,"scale");light=glGetUniformLocation(program,"light");
    glGenBuffers(1,&buffer);glBindBuffer(GL_ARRAY_BUFFER,buffer);glBufferData(GL_ARRAY_BUFFER,sizeof vertices,vertices,GL_STATIC_DRAW);glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,0,0);glEnableVertexAttribArray(0);
    glViewport(0,0,width,height);glUniform1f(aspect,(float)width/height);
    if(probing&&glGetError()!=GL_NO_ERROR)return reject("unsupported","GLES2 workload setup failed.");
    printf("{\"suite_version\":\"" G3_SUITE_VERSION "\",\"workload_id\":\"" G3_WORKLOAD_ID "\",\"renderer\":");json_string((const char*)glGetString(GL_RENDERER));printf(",\"driver\":");json_string((const char*)glGetString(GL_VERSION));printf(",\"width\":%d,\"height\":%d,\"vsync\":false",width,height);
    printf(",\"display_server\":");json_string(SDL_GetCurrentVideoDriver());
    if(probing){printf(",\"status\":\"ready\",\"reason\":\"Requested GLES2 context, shaders, resolution and swap interval available.\"}");glDeleteBuffers(1,&buffer);glDeleteProgram(program);SDL_GL_DeleteContext(ctx);SDL_DestroyWindow(window);SDL_Quit();return 0;}
    printf(",\"scenes\":[");
    for(scene=0;scene<5;scene++) {
        const size_t capacity=1000000; double *times=malloc(capacity*sizeof(double)),sum=0,squares=0;
        Uint64 freq=SDL_GetPerformanceFrequency(),start=SDL_GetPerformanceCounter(),last=start; size_t frames=0; double elapsed=0;
        if(!times)return 3;
        if(scene==4){glEnable(GL_BLEND);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);}else glDisable(GL_BLEND);
        while(elapsed<5.0){
            SDL_Event event;while(SDL_PollEvent(&event)){if(event.type==SDL_QUIT||(event.type==SDL_KEYDOWN&&event.key.keysym.sym==SDLK_ESCAPE)){free(times);return 4;}}
            glClearColor(0.015f,0.02f,0.045f,1);glClear(GL_COLOR_BUFFER_BIT);
            glUniform1f(light,scene==2?1.0f:0.0f);
            for(int i=0;i<counts[scene];i++){
                float t=(float)elapsed, angle=i*2.399963f;
                float radius=0.15f+0.8f*(float)(i%31)/31;
                glUniform1f(phase,t*0.7f+i*0.1f);
                glUniform2f(offset,sinf(angle+t*0.2f)*radius*1.5f,cosf(angle+t*0.2f)*radius);
                glUniform1f(scale,scene==4?0.15f:0.065f);glDrawArrays(GL_TRIANGLE_STRIP,0,4);
            }
            glFinish();SDL_GL_SwapWindow(window);
            Uint64 end=SDL_GetPerformanceCounter();double dt=(double)(end-last)/freq;last=end;elapsed=(double)(end-start)/freq;
            if(frames>=capacity){fprintf(stderr,"frame buffer exhausted\n");free(times);return 3;}
            times[frames++]=dt;sum+=dt;squares+=dt*dt;
        }
        if(glGetError()!=GL_NO_ERROR){fprintf(stderr,"GL error; result discarded\n");free(times);return 2;}
        qsort(times,frames,sizeof(double),compare);size_t tail=(frames+99)/100;double slow=0;for(size_t i=frames-tail;i<frames;i++)slow+=times[i];
        printf("%s{\"scene\":%d,\"objects\":%d,\"frames\":%lu,\"seconds\":%.6f,\"average_fps\":%.6f,\"one_percent_low_fps\":%.6f,\"frame_ms\":%.6f,\"variance_ms2\":%.6f}",scene?",":"",scene+1,counts[scene],(unsigned long)frames,sum,frames/sum,tail/slow,1000*sum/frames,1e6*fmax(0,squares/frames-(sum/frames)*(sum/frames)));
        fflush(stdout);free(times);
    }
    printf("]}");glDeleteBuffers(1,&buffer);glDeleteProgram(program);SDL_GL_DeleteContext(ctx);SDL_DestroyWindow(window);SDL_Quit();return 0;
}
