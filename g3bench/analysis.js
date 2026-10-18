/* Offline cross-board analysis. Never uploads loaded JSON files. */
(() => {
  const section=document.createElement('section');section.className='panel wide';
  section.innerHTML='<h2>Warnings and stock-setting recommendations</h2><div id="advice"></div><details><summary>Display, OpenGL, Vulkan and USB diagnostic evidence</summary><pre id="diagnostic-evidence"></pre></details><h2>Thermal profile by stage</h2><p>Sample averages and peaks, not a continuous thermal model. No sensor means unavailable.</p><div class="scroll"><table><thead><tr><th>Stage</th><th>Samples</th><th>Average °C</th><th>Peak °C</th><th>Average CPU %</th></tr></thead><tbody id="stage-thermal"></tbody></table></div>';
  $('charts').closest('section').parentElement.after(section);
  for(const entry of JSON.parse($('recommendations').textContent)){const p=document.createElement('p'),b=document.createElement('b');b.textContent=entry.level.toUpperCase()+' · '+entry.title+' — ';p.append(b,document.createTextNode(entry.detail+' '));if(entry.reference?.startsWith('https://')){const a=document.createElement('a');a.href=entry.reference;a.textContent='Reference';a.target='_blank';a.rel='noopener';p.append(a);} $('advice').append(p);}
  const actual=data.results.showcase,summary=document.createElement('p');summary.textContent=actual?'Actual 3D backend: '+[actual.rendering_method,actual.rendering_driver,'API '+(actual.api_version??'unavailable'),actual.display_server,'Godot '+actual.engine_version].filter(Boolean).join(' · '):'Native graphics: '+[data.results.gpu?.renderer,data.results.gpu?.driver,data.results.gpu?.display_server].filter(Boolean).join(' · ');$('diagnostic-evidence').closest('details').before(summary);
  $('diagnostic-evidence').textContent=JSON.stringify(data.diagnostics??{status:'Not collected in this older run'},null,2);
  const stages=new Map();for(const s of data.telemetry??[]){const stage=s.stage??'Unknown';if(!stages.has(stage))stages.set(stage,[]);stages.get(stage).push(s);}
  const mean=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:null;
  const finite=n=>typeof n==='number'&&Number.isFinite(n);
  for(const [stage,samples] of stages){const temps=samples.map(s=>s.temperature_c).filter(finite),load=samples.map(s=>s.cpu_utilization).filter(finite);row('stage-thermal',[stage,samples.length,fmt(mean(temps),2),fmt(temps.length?Math.max(...temps):null,2),fmt(mean(load),1)]);}
  const comparePanel=document.createElement('section');comparePanel.className='panel wide';comparePanel.innerHTML='<h2>Cross-board workload comparison</h2><p>Load results with Compare saved runs above, then use Print / save PDF for this comparison. Deltas use the first matching workload/settings as reference. Unsupported work stays unavailable. These are measured rates, not board-adjusted ratings. Mixed settings have separate groups.</p><details><summary>Loaded run configurations</summary><pre id="comparison-configs"></pre></details><div id="comparison-plots"></div><h3>Repeated configuration summary</h3><p>Median and range describe loaded runs only; they do not establish statistical significance.</p><div class="scroll"><table><thead><tr><th>Configuration / workload</th><th>N</th><th>Median</th><th>Min–max</th></tr></thead><tbody id="repeat-summary"></tbody></table></div><div class="scroll"><table><thead><tr><th>Run / board</th><th>Workload</th><th>Measured result</th><th>Change / matching group</th></tr></thead><tbody id="raw-comparison"></tbody></table></div>';
  document.querySelector('footer').before(comparePanel);
  const runs=[],references=new Map(),repeatGroups=new Map();
  function add(r){
    if(!r.hardware||!r.results||!r.configuration)throw Error('Not a benchmark result');
    runs.push(r);const title=(r.configuration.label??'Run')+' · '+r.hardware.board_model+' / suite '+r.benchmark_version;
    function metric(name,value,unit,group,lower=false){
      if(!finite(value))return;
      const repeatKey=JSON.stringify([r.hardware.hostname,r.hardware.board_model,r.configuration.label,r.hardware.kernel,r.native_build,group,name,unit]);
      if(!repeatGroups.has(repeatKey))repeatGroups.set(repeatKey,{title:(r.configuration.label??'Run')+' / '+r.hardware.board_model+' / '+name,unit,values:[]});repeatGroups.get(repeatKey).values.push(value);
      const key=JSON.stringify([name,unit,group]);const old=references.get(key);if(!old)references.set(key,{value,index:references.size+1});const reference=references.get(key);
      const delta=old&&old.value>0?((value/old.value-1)*100):null;
      row('raw-comparison',[title,name,fmt(value,2)+' '+unit,(delta===null?'Reference':(delta>=0?'+':'')+fmt(delta,1)+'%'+(lower?' · lower is better':''))+' · group '+reference.index]);
    }
    for(const category of ['cpu','memory'])for(const [name,v] of Object.entries(r.results[category]??{}))if(v&&typeof v==='object'&&'value'in v)metric(category+' / '+name,v.value,v.unit,[r.native_build?.workload_id??'baseline-0.1',category==='memory'?r.configuration.memory_buffer_bytes:null,r.configuration.threads??1]);
    for(const scene of r.results.gpu?.scenes??[])metric('GLES / scene '+scene.scene,scene.average_fps,'FPS',[r.benchmark_version,r.native_build?.workload_id??r.workload_id,r.results.gpu.width,r.results.gpu.height,r.configuration.fullscreen,r.results.gpu.vsync]);
    const g=r.results.showcase;for(const scene of g?.scenes??[])metric('Godot / '+scene.name,scene.average_fps,'FPS',[g.workload_id,g.engine_version,g.rendering_method,g.rendering_driver??'opengl3',g.width,g.height,r.configuration.fullscreen]);
    const c=r.results.storage?.configuration??r.configuration;
    for(const d of r.results.storage?.drives??[])for(const [name,v] of Object.entries(d.tests??{}))if(v.status==='passed')metric('Drive '+(d.target.model??d.target.media??'')+' / '+name,v.mb_s,'MB/s',[c.storage_workload??r.workload_id,c.size_mib,c.random_seconds,c.direct,c.ioengine,c.iodepth,c.fio_version]);
    const load=r.results.load;if(load)metric('Sustained SHA256',load.mb_s,'MB/s',[load.workload_id,load.workers,load.openssl]);
    const n=r.results.network;if(n){for(const key of ['download_mbps','upload_mbps'])metric('Network / '+key,n[key],'Mbps',[n.endpoint,n.method]);metric('HTTP response latency',n.latency_ms,'ms',[n.endpoint,n.latency_kind],true);}
    $('repeat-summary').replaceChildren();for(const group of repeatGroups.values()){const values=[...group.values].sort((a,b)=>a-b),middle=Math.floor(values.length/2),median=values.length%2?values[middle]:(values[middle-1]+values[middle])/2;row('repeat-summary',[group.title,values.length,fmt(median,2)+' '+group.unit,fmt(values[0],2)+'–'+fmt(values.at(-1),2)+' '+group.unit]);}
    $('comparison-configs').textContent=JSON.stringify(runs.map(x=>({board:x.hardware.board_model,suite:x.benchmark_version,configuration:x.configuration,native_build:x.native_build,renderer:x.results.showcase?.renderer,api:x.results.showcase?.api_version,display_server:x.results.showcase?.display_server})),null,2);
    plot();
  }
  function plot(){
    $('comparison-plots').replaceChildren();const colors=['#62efd0','#b6a1ff','#ffca85','#63b8ff','#ee97c8'];
    for(const [field,label,unit] of [['temperature_c','Temperature versus elapsed time','°C'],['cpu_utilization','CPU load versus elapsed time','%'],['disk_read_mb_s','System-wide disk read activity','MB/s'],['disk_write_mb_s','System-wide disk write activity','MB/s']]){
      const measured=runs.map(r=>({r,s:(r.telemetry??[]).filter(s=>finite(s[field])&&finite(s.elapsed_seconds))})).filter(x=>x.s.length);if(!measured.length)continue;
      const max=Math.max(1,...measured.flatMap(x=>x.s.map(s=>s[field]))),end=Math.max(1,...measured.flatMap(x=>x.s.map(s=>s.elapsed_seconds)));
      const box=document.createElement('div');box.className='chart';const h=document.createElement('p');h.textContent=label+' · 0–'+fmt(max,1)+' '+unit+' · 0–'+fmt(end,1)+' s';const svg=svgNode('svg',{viewBox:'0 0 800 180',role:'img','aria-label':h.textContent});
      measured.forEach(({r,s},i)=>{svg.append(svgNode('polyline',{points:s.map(v=>[30+750*v.elapsed_seconds/end,155-140*v[field]/max].join(',')).join(' '),stroke:colors[i%colors.length],'stroke-width':2,fill:'none'}));const legend=document.createElement('span');legend.textContent=(i?' · ':'')+(r.configuration.label??'Run')+' / '+r.hardware.board_model;legend.style.color=colors[i%colors.length];box.append(legend);});box.prepend(h,svg);$('comparison-plots').append(box);
    }
  }
  add(data);for(const r of JSON.parse($('extra-results').textContent))add(r);
  $('files').addEventListener('change',async e=>{for(const file of e.target.files){try{add(JSON.parse(await file.text()));}catch(error){set('errors','Comparison load failed: '+error.message);}}});
  if(data.results.load)row('metrics',['Sustained SHA256 / '+data.results.load.workers+' workers',fmt(data.results.load.mb_s,2)+' MB/s',fmt(data.results.load.seconds,2)+' s']);
  if(data.results.network){const n=data.results.network;
    const panel=document.createElement('section');panel.className='panel wide';const heading=document.createElement('h2');heading.textContent='Network send / receive trials';panel.append(heading);const note=document.createElement('p');note.textContent=(n.endpoint??'')+' · '+(n.method??'');panel.append(note);const trials=n.trials??[],max=Math.max(1,...trials.map(t=>t.mbps));for(const t of trials){const label=document.createElement('p');label.textContent=t.direction+' '+(t.trial??'')+' · '+fmt(t.mbps,2)+' Mbps';const track=document.createElement('div');track.className='bar-track';const fill=document.createElement('div');fill.className='bar-fill';fill.style.width=(t.mbps/max*100)+'%';track.append(fill);panel.append(label,track);}comparePanel.before(panel);
for(const key of ['download_mbps','upload_mbps'])row('metrics',['Network / '+key,fmt(n[key],2)+' Mbps',n.method]);row('metrics',['HTTP response start',fmt(n.latency_ms,2)+' ms','Variation '+fmt(n.latency_variation_ms,2)+' ms; not ICMP ping']);for(const t of n.trials??[])row('metrics',[t.direction+' / trial '+t.trial,fmt(t.mbps,2)+' Mbps',fmt(t.seconds,3)+' s · '+fmt(t.bytes)+' bytes']);}
})();
