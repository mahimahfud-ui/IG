// mahimahfud — original cinematic 3D photo-universe.
// Real uploaded media only; no demo gallery assets are generated.
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js";

const REDUCED=matchMedia("(prefers-reduced-motion: reduce)").matches;
const MOBILE=matchMedia("(max-width:760px)").matches;
let sceneState=null;

function tune(renderer,camera){camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight,false);renderer.setPixelRatio(Math.min(devicePixelRatio,MOBILE?1:1.35))}

function intro(){
 let seen=false;try{seen=sessionStorage.getItem("mmf-intro-v7")==="1"}catch{}
 if(seen||REDUCED)return Promise.resolve();
 const host=document.getElementById("intro"),target=document.getElementById("introCanvas");
 if(!host||!target)return Promise.resolve();host.classList.remove("hidden");
 return new Promise(done=>{
  const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:"high-performance"});renderer.setPixelRatio(Math.min(devicePixelRatio,MOBILE?1:1.35));renderer.setSize(innerWidth,innerHeight,false);renderer.domElement.style.cssText="position:absolute;inset:0;width:100%;height:100%";target.appendChild(renderer.domElement);
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(48,innerWidth/innerHeight,.1,90),world=new THREE.Group();scene.add(world);camera.position.z=10;
  const count=MOBILE?100:190,pos=new Float32Array(count*3);for(let i=0;i<count;i++){pos[i*3]=(Math.random()-.5)*22;pos[i*3+1]=(Math.random()-.5)*14;pos[i*3+2]=-Math.random()*44}
  const sg=new THREE.BufferGeometry();sg.setAttribute("position",new THREE.BufferAttribute(pos,3));world.add(new THREE.Points(sg,new THREE.PointsMaterial({color:0xbfd0ff,size:MOBILE?.03:.024,transparent:true,opacity:.46,depthWrite:false,blending:THREE.AdditiveBlending})));
  const orb=new THREE.Mesh(new THREE.SphereGeometry(1.85,42,42),new THREE.MeshBasicMaterial({color:0x0b1322,transparent:true,opacity:.9,wireframe:true}));orb.position.z=-3;world.add(orb);
  const ring=new THREE.Mesh(new THREE.TorusGeometry(3.15,.012,12,180),new THREE.MeshBasicMaterial({color:0xa8bdff,transparent:true,opacity:.25}));ring.rotation.set(.9,.15,0);ring.position.z=-3;world.add(ring);
  let last=performance.now(),raf=0,t=0,dead=false;
  const resize=()=>tune(renderer,camera);addEventListener("resize",resize);
  const loop=now=>{if(dead)return;raf=requestAnimationFrame(loop);const dt=Math.min(.05,(now-last)/1000);last=now;t+=dt;world.rotation.y+=dt*.16;world.rotation.x=Math.sin(t*.4)*.04;orb.rotation.y+=dt*.045;ring.rotation.z+=dt*.11;renderer.render(scene,camera)};loop(performance.now());
  const end=()=>{if(dead)return;dead=true;cancelAnimationFrame(raf);removeEventListener("resize",resize);try{sessionStorage.setItem("mmf-intro-v7","1")}catch{};host.style.transition="opacity .75s ease";host.style.opacity="0";setTimeout(()=>{host.classList.add("hidden");host.style.opacity="";renderer.dispose();renderer.domElement.remove();done()},780)};
  window.addEventListener("mmf-skip-intro",end,{once:true});window.addEventListener("pointerdown",end,{once:true});window.addEventListener("keydown",end,{once:true});setTimeout(end,3200);
 });
}

function atmosphere(root){
 if(REDUCED)return;
 const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:"high-performance"});renderer.domElement.style.cssText="position:absolute;inset:0;width:100%;height:100%;pointer-events:none";root.appendChild(renderer.domElement);
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(46,innerWidth/innerHeight,.1,160),world=new THREE.Group();scene.add(world);camera.position.z=10;
 const starsN=MOBILE?850:1700,sp=new Float32Array(starsN*3),sv=new Float32Array(starsN);for(let i=0;i<starsN;i++){sp[i*3]=(Math.random()-.5)*30;sp[i*3+1]=(Math.random()-.5)*18;sp[i*3+2]=-Math.random()*60;sv[i]=.002+Math.random()*.01}const sg=new THREE.BufferGeometry();sg.setAttribute("position",new THREE.BufferAttribute(sp,3));world.add(new THREE.Points(sg,new THREE.PointsMaterial({color:0xb9c8ff,size:MOBILE?.018:.021,transparent:true,opacity:.46,depthWrite:false,blending:THREE.AdditiveBlending})));
 const dustN=MOBILE?180:360,dp=new Float32Array(dustN*3);for(let i=0;i<dustN;i++){dp[i*3]=(Math.random()-.5)*18;dp[i*3+1]=(Math.random()-.5)*12;dp[i*3+2]=-(Math.random()*16+1)}const dg=new THREE.BufferGeometry();dg.setAttribute("position",new THREE.BufferAttribute(dp,3));world.add(new THREE.Points(dg,new THREE.PointsMaterial({color:0xf0f4ff,size:MOBILE?.025:.032,transparent:true,opacity:.2,depthWrite:false,blending:THREE.AdditiveBlending})));
 const orb=new THREE.Mesh(new THREE.SphereGeometry(2.3,52,52),new THREE.MeshBasicMaterial({color:0x080f1c,transparent:true,opacity:.9,wireframe:true}));orb.position.z=-3.2;world.add(orb);
 const core=new THREE.Mesh(new THREE.SphereGeometry(.82,32,32),new THREE.MeshBasicMaterial({color:0x192944,transparent:true,opacity:.48}));core.position.z=-1.7;world.add(core);
 const halo=new THREE.Mesh(new THREE.SphereGeometry(2.7,44,44),new THREE.MeshBasicMaterial({color:0x7399ff,transparent:true,opacity:.03,depthWrite:false,blending:THREE.AdditiveBlending}));halo.position.z=-3.2;world.add(halo);
 const ringA=new THREE.Mesh(new THREE.TorusGeometry(3.5,.012,14,220),new THREE.MeshBasicMaterial({color:0xa6bcff,transparent:true,opacity:.25}));ringA.rotation.set(.88,.14,0);ringA.position.z=-3.2;world.add(ringA);
 const ringB=new THREE.Mesh(new THREE.TorusGeometry(4.55,.008,14,240),new THREE.MeshBasicMaterial({color:0x7995d5,transparent:true,opacity:.12}));ringB.rotation.set(1.18,-.5,.15);ringB.position.z=-3.2;world.add(ringB);
 const frames=new THREE.Group();frames.position.z=-3.2;world.add(frames);let frameItems=[];
 function clearFrames(){while(frames.children.length){const child=frames.children.pop();child.traverse(o=>{if(o.geometry)o.geometry.dispose();if(o.material){if(o.material.map)o.material.map.dispose();o.material.dispose()}})}}
 function addMedia(items){clearFrames();frameItems=[];const usable=(items||[]).filter(m=>m&&m.original_url).slice(0,21);if(!usable.length)return;const GA=Math.PI*(3-Math.sqrt(5));usable.forEach((m,i)=>{const y=1-(i/Math.max(1,usable.length-1))*2,rad=Math.sqrt(Math.max(0,1-y*y)),theta=i*GA,x=Math.cos(theta)*rad,z=Math.sin(theta)*rad,g=new THREE.Group(),w=MOBILE?.75:1.02,h=w*(m.type==="video"?0.6:.72);g.position.set(x*4.55,y*4.55,z*4.55);g.rotation.y=Math.atan2(x,z);g.rotation.x=Math.asin(Math.max(-1,Math.min(1,y)));g.userData.phase=i*.69;if(m.type==="video"){const v=document.createElement("video");v.src=m.original_url;v.muted=true;v.loop=true;v.playsInline=true;v.preload="metadata";v.crossOrigin="anonymous";const tex=new THREE.VideoTexture(v);tex.colorSpace=THREE.SRGBColorSpace;const mat=new THREE.MeshBasicMaterial({map:tex,transparent:true,opacity:MOBILE?.32:.48,depthWrite:false});g.add(new THREE.Mesh(new THREE.PlaneGeometry(w,h),mat));v.play().catch(()=>{})}else{const tex=new THREE.TextureLoader().load(m.thumbnail_url||m.original_url);tex.colorSpace=THREE.SRGBColorSpace;g.add(new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map:tex,transparent:true,opacity:MOBILE?.32:.48,depthWrite:false})))}g.add(new THREE.Mesh(new THREE.PlaneGeometry(w*1.05,h*1.05),new THREE.MeshBasicMaterial({color:0xbccaff,transparent:true,opacity:.18,wireframe:true,depthWrite:false,blending:THREE.AdditiveBlending})));frames.add(g);frameItems.push(g)})}
 if(window.__MMF_MEDIA__)addMedia(window.__MMF_MEDIA__);else window.addEventListener("mmf-media-ready",e=>addMedia(e.detail));
 let px=0,py=0,sx=0,sy=0,scroll=0,scrollTarget=0,time=0,last=performance.now(),raf=0,visible=true;
 addEventListener("pointermove",e=>{px=e.clientX/innerWidth-.5;py=e.clientY/innerHeight-.5},{passive:true});addEventListener("scroll",()=>{scrollTarget=Math.max(0,Math.min(1,scrollY/(innerHeight*.16)))},{passive:true});
 const resize=()=>tune(renderer,camera);resize();addEventListener("resize",resize);
 const pause=()=>{visible=false;cancelAnimationFrame(raf)},resume=()=>{visible=true;last=performance.now();raf=requestAnimationFrame(loop)};document.addEventListener("visibilitychange",()=>document.hidden?pause():resume());
 function loop(now){if(!visible)return;raf=requestAnimationFrame(loop);const dt=Math.min(.05,(now-last)/1000);last=now;time+=dt;sx+=(px-sx)*.035;sy+=(py-sy)*.035;scroll+=(scrollTarget-scroll)*.075;camera.position.x=sx*1.3;camera.position.y=-sy*.85;camera.position.z=10-scroll*2.2;camera.lookAt(0,0,-3.2);world.rotation.y+=dt*.012;world.rotation.x=Math.sin(time*.16)*.015;
  const s=sg.attributes.position.array;for(let i=0;i<starsN;i++){s[i*3+2]+=sv[i]*(dt*60);if(s[i*3+2]>4){s[i*3+2]=-60;s[i*3]=(Math.random()-.5)*30;s[i*3+1]=(Math.random()-.5)*18}}sg.attributes.position.needsUpdate=true;
  const d=dg.attributes.position.array;for(let i=0;i<dustN;i++){d[i*3+2]+=dt*.03;if(d[i*3+2]>2)d[i*3+2]=-17}dg.attributes.position.needsUpdate=true;
  orb.rotation.y+=dt*.035;orb.rotation.x+=dt*.01;core.rotation.y-=dt*.02;halo.scale.setScalar(1+.045*Math.sin(time*.7));ringA.rotation.z+=dt*.09;ringB.rotation.z-=dt*.06;frames.rotation.y-=dt*.022;frames.rotation.x=Math.sin(time*.22)*.03;
  frameItems.forEach((f,i)=>{f.position.y+=Math.sin(time*.24+f.userData.phase)*dt*.01;f.rotation.z=Math.sin(time*.22+f.userData.phase)*.018;const q=.012*Math.sin(time*1.1+f.userData.phase);f.scale.setScalar(1+q)});renderer.render(scene,camera);
 }
 resume();renderer.domElement.addEventListener("webglcontextlost",e=>{e.preventDefault();pause();renderer.domElement.remove()});
}
export {intro,atmosphere};