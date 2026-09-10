import * as THREE from './vendor/three.module.js';
export function mountCharacter(home,modalHost,dialog){
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;let bowStart=-100,renderer,scene,camera,rig,upper,head,petals=[],canvasParent=home;
function resize(){if(!renderer)return;const w=canvasParent.clientWidth,h=canvasParent.clientHeight;if(!w||!h)return;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}
function mat(color,roughness=.65){return new THREE.MeshStandardMaterial({color,roughness});}
function mesh(geo,material,parent,x=0,y=0,z=0){const m=new THREE.Mesh(geo,material);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;}
function ball(parent,material,x,y,z,sx,sy,sz){const m=mesh(new THREE.SphereGeometry(1,32,24),material,parent,x,y,z);m.scale.set(sx,sy,sz);return m;}
function line(parent,pts,color,r=.014){const curve=new THREE.CatmullRomCurve3(pts.map(p=>new THREE.Vector3(...p)));return mesh(new THREE.TubeGeometry(curve,30,r,8,false),color,parent);}
function flower(parent,x,y,z,size,color){const g=new THREE.Group();g.position.set(x,y,z);parent.add(g);for(let i=0;i<5;i++){const a=i*Math.PI*2/5;const p=ball(g,color,Math.sin(a)*size*.62,Math.cos(a)*size*.62,0,size*.45,size*.65,size*.19);p.rotation.z=-a;}ball(g,mat('#d3ad63'),0,0,size*.12,size*.21,size*.21,size*.16);return g;}
function kimonoTexture(){
 const c=document.createElement('canvas');c.width=c.height=1024;const ctx=c.getContext('2d');
 const grad=ctx.createLinearGradient(0,0,0,1024);grad.addColorStop(0,'#f5cbb7');grad.addColorStop(.55,'#edaf94');grad.addColorStop(1,'#d98878');ctx.fillStyle=grad;ctx.fillRect(0,0,1024,1024);
 // Original camellia clusters, fine leaves and a woven dotted ground.
 ctx.fillStyle='#fff6e02b';for(let y=0;y<1024;y+=20)for(let x=0;x<1024;x+=20)ctx.fillRect(x,y,1,2);
 for(let i=0;i<15;i++){const x=(i*281+85)%1024,y=(i*187+120)%1024;ctx.save();ctx.translate(x,y);ctx.rotate(i*.9);
 ctx.fillStyle='#789f8b';for(const sign of [-1,1]){ctx.beginPath();ctx.ellipse(sign*31,16,21,7,sign*.5,0,Math.PI*2);ctx.fill();}
 for(let j=0;j<6;j++){ctx.save();ctx.rotate(j*Math.PI/3);ctx.fillStyle=i%3?'#fff4de':'#d9746e';ctx.beginPath();ctx.ellipse(0,13,12,18,0,0,Math.PI*2);ctx.fill();ctx.restore();}
 ctx.fillStyle='#e3b15b';ctx.beginPath();ctx.arc(0,0,7,0,Math.PI*2);ctx.fill();ctx.restore();}
 const tex=new THREE.CanvasTexture(c);tex.colorSpace=THREE.SRGBColorSpace;return tex;
}
// Tapered sculpted locks, rather than rows of round primitives.
function lock(parent,points,width,material){
 const path=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)));const vertices=[],indices=[];const rows=28,cols=12;
 for(let i=0;i<=rows;i++){const t=i/rows,p=path.getPoint(t),w=width*Math.pow(Math.sin(Math.PI*(t*.92+.04)),.55)*(1-t*.32);
 for(let j=0;j<=cols;j++){const u=j/cols*2-1;vertices.push(p.x+u*w,p.y,p.z+Math.sqrt(Math.max(0,1-u*u))*width*.43);}}
 for(let i=0;i<rows;i++)for(let j=0;j<cols;j++){const a=i*(cols+1)+j,b=a+cols+1;indices.push(a,b,a+1,a+1,b,b+1);}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setIndex(indices);g.computeVertexNormals();return mesh(g,material,parent);
}
function animeFace(parent){
 const c=document.createElement('canvas');c.width=c.height=1024;const x=c.getContext('2d');
 // Painted eyes lie on the curved face, with almond outlines and layered amber irises.
 for(const side of [-1,1]){const cx=512+side*220,cy=475;
 x.save();x.translate(cx,cy);x.scale(side,1);
 x.fillStyle='#fffdf4';x.beginPath();x.moveTo(-114,0);x.bezierCurveTo(-65,-98,54,-112,116,-29);x.bezierCurveTo(109,123,-84,120,-114,0);x.fill();
 x.save();x.clip();const iris=x.createLinearGradient(0,-90,0,110);iris.addColorStop(0,'#493044');iris.addColorStop(.45,'#98634d');iris.addColorStop(1,'#e8b976');x.fillStyle=iris;x.beginPath();x.ellipse(0,12,66,101,0,0,Math.PI*2);x.fill();x.fillStyle='#3e2b39';x.beginPath();x.ellipse(0,-4,29,68,0,0,Math.PI*2);x.fill();
 x.fillStyle='#fff';x.beginPath();x.ellipse(-24,-40,22,27,-.2,0,Math.PI*2);x.fill();x.beginPath();x.arc(29,48,10,0,Math.PI*2);x.fill();x.fillStyle='#fbe4b5';x.beginPath();x.ellipse(-8,77,22,7,0,0,Math.PI*2);x.fill();x.restore();
 x.strokeStyle='#573d38';x.lineWidth=14;x.lineCap='round';x.beginPath();x.moveTo(-114,0);x.bezierCurveTo(-65,-98,54,-112,116,-29);x.lineTo(137,-53);x.stroke();x.lineWidth=5;x.strokeStyle='#986951';x.beginPath();x.moveTo(-98,61);x.quadraticCurveTo(0,111,96,61);x.stroke();
 x.lineWidth=8;x.strokeStyle='#805342';x.beginPath();x.moveTo(-80,-144);x.quadraticCurveTo(5,-171,92,-130);x.stroke();x.restore();
 const blush=x.createRadialGradient(cx+side*58,665,2,cx+side*58,665,89);blush.addColorStop(0,'#ef9d9760');blush.addColorStop(1,'#ef9d9700');x.fillStyle=blush;x.fillRect(cx+side*58-90,575,180,180);}
 x.strokeStyle='#dcaaa0';x.lineWidth=6;x.lineCap='round';x.beginPath();x.moveTo(516,607);x.quadraticCurveTo(504,622,520,622);x.stroke();
 x.fillStyle='#bc6c69';x.beginPath();x.moveTo(467,729);x.quadraticCurveTo(512,750,557,729);x.quadraticCurveTo(512,799,467,729);x.fill();x.fillStyle='#f0b0a5';x.beginPath();x.ellipse(512,760,22,9,0,0,Math.PI*2);x.fill();
 const texture=new THREE.CanvasTexture(c);texture.colorSpace=THREE.SRGBColorSpace;const material=new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false,side:THREE.DoubleSide});
 const pos=[],uv=[],ids=[];const n=44;
 for(let i=0;i<=n;i++)for(let j=0;j<=n;j++){const u=j/n,v=i/n,px=(u-.5)*1.02,py=(.5-v)*.88-.05;const r=1-(px/.57)**2-((py+.055)/.52)**2;pos.push(px,py,.13+.453*Math.sqrt(Math.max(.025,r))+.008);uv.push(u,1-v);}
 for(let i=0;i<n;i++)for(let j=0;j<n;j++){const a=i*(n+1)+j,b=a+n+1;ids.push(a,b,a+1,a+1,b,b+1);}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(ids);g.computeVertexNormals();const face=mesh(g,material,parent);face.castShadow=false;face.receiveShadow=false;
}
function sleeve(parent,side,fabric){
 const sh=new THREE.Shape();sh.moveTo(.26,.54);sh.quadraticCurveTo(.53,.59,.78,.25);sh.lineTo(.86,-.48);sh.quadraticCurveTo(.69,-.62,.43,-.48);sh.lineTo(.32,.03);sh.closePath();
 const geo=new THREE.ExtrudeGeometry(sh,{depth:.28,bevelEnabled:true,bevelThickness:.045,bevelSize:.055,bevelSegments:4,steps:1,curveSegments:18});
 const m=mesh(geo,fabric,parent,0,0,-.06);m.scale.x=side;return m;
}
try{
renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;home.replaceChildren(renderer.domElement);
scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(32,1,.1,100);camera.position.set(0,2.6,8.3);camera.lookAt(0,1.68,0);scene.add(new THREE.HemisphereLight('#fff5e6','#b6a9ab',2.2));const key=new THREE.DirectionalLight('#fff6e6',2.6);key.position.set(-3,6,5);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-4;key.shadow.camera.right=4;key.shadow.camera.top=5;key.shadow.camera.bottom=-4;key.shadow.bias=-.001;key.shadow.normalBias=.025;scene.add(key);const rim=new THREE.DirectionalLight('#ffd9e2',2);rim.position.set(4,3,-3);scene.add(rim);
const cream=mat('#f6eedc'),skin=mat('#ffe9d8'),hair=mat('#663c30',.8),pink=mat('#d994a6'),dark=mat('#40313d'),gold=mat('#c7a464',.4),obi=mat('#86a99c');const fabric=new THREE.MeshStandardMaterial({map:kimonoTexture(),roughness:.88});
// Small sandals, a fitted kimono skirt and a waist pivot shared by the upper body.
rig=new THREE.Group();rig.rotation.y=-.10;scene.add(rig);
for(const side of [-1,1]){ball(rig,mat('#b88f70'),side*.19,.19,.15,.16,.07,.27);ball(rig,cream,side*.19,.26,.13,.13,.075,.23);line(rig,[[side*.19-.10,.29,.25],[side*.19,.31,.12],[side*.19+.10,.29,.25]],mat('#c96d5b'),.022);}
const skirt=mesh(new THREE.CylinderGeometry(.33,.46,1.02,64),fabric,rig,0,.83,0);skirt.scale.z=.80;
line(rig,[[.20,1.28,.27],[.13,.80,.35],[.10,.33,.38]],cream,.014);
upper=new THREE.Group();upper.position.set(0,1.29,0);rig.add(upper);
const torso=mesh(new THREE.CylinderGeometry(.29,.34,.67,64),fabric,upper,0,.27,0);torso.scale.z=.80;ball(upper,skin,0,.67,0,.12,.18,.115);
line(upper,[[-.20,.58,.18],[-.06,.35,.285],[.13,.13,.31]],cream,.040);line(upper,[[.20,.58,.18],[.04,.36,.29],[-.13,.12,.32]],cream,.040);
const belt=mesh(new THREE.CylinderGeometry(.355,.355,.24,64),obi,upper,0,-.015,0);belt.scale.z=.87;
line(upper,[[-.28,.005,.19],[0,.005,.315],[.28,.005,.19]],cream,.016);flower(upper,.07,.005,.338,.045,mat('#f5d893'));
for(const side of [-1,1]){const bow=ball(upper,obi,side*.20,.02,-.30,.23,.16,.09);bow.rotation.z=side*.25;sleeve(upper,side,fabric);}
for(const side of [-1,1]){const hand=ball(upper,skin,side*.085,.075,.35,.105,.045,.055);hand.rotation.z=side*.20;}
head=new THREE.Group();head.position.set(0,1.08,.005);head.scale.setScalar(1.24);upper.add(head);
ball(head,hair,0,.10,-.14,.61,.59,.48);ball(head,skin,0,-.055,.13,.57,.52,.453);
const hairLight=mat('#80503b',.8);hair.side=THREE.DoubleSide;hairLight.side=THREE.DoubleSide;
// Long back hair, softly split bangs and two curved face-framing strands.
for(let i=0;i<7;i++){const a=(i-3)*.15;lock(head,[[a,.45,-.35],[a*1.4,.05,-.46],[a*1.5,-.56,-.34],[a*1.35,-.91,-.20]],.19,i%3===0?hairLight:hair);}
lock(head,[[-.08,.59,.03],[-.24,.43,.36],[-.32,.22,.48],[-.40,.05,.43]],.24,hair);
lock(head,[[.08,.59,.01],[.16,.43,.38],[.20,.24,.51],[.29,.15,.48]],.23,hairLight);
lock(head,[[-.04,.59,.09],[-.07,.43,.44],[-.09,.26,.52],[-.14,.19,.51]],.11,hairLight);
for(const side of [-1,1]){lock(head,[[side*.46,.38,.20],[side*.55,.0,.29],[side*.51,-.43,.26],[side*.39,-.70,.20]],.105,hair);}
animeFace(head);
// Asymmetric camellia hairpin with a sage cord: an original ornament.
const pin=new THREE.Group();pin.position.set(-.55,.18,.17);pin.rotation.z=.3;head.add(pin);flower(pin,0,0,0,.12,mat('#ed947e'));flower(pin,.10,-.09,.01,.065,cream);
line(pin,[[0,-.06,0],[-.08,-.19,0],[0,-.26,.01],[.06,-.17,0],[0,-.06,0]],obi,.018);
// A restrained arrangement of 3D petals gives depth to the quiet background.
for(let i=0;i<5;i++){const p=ball(scene,i%2?pink:cream,Math.sin(i*2.4)*1.9, .6+(i*.39)%2.8,Math.cos(i)*.6-.7,.045,.077,.018);p.rotation.set(i*.4,0,i);p.userData={x:p.position.x,y:p.position.y,phase:i};petals.push(p);}const ro=new ResizeObserver(resize);ro.observe(home);ro.observe(modalHost);resize();let pointer=0;home.addEventListener('pointermove',e=>{pointer=((e.clientX-home.getBoundingClientRect().left)/home.clientWidth-.5)*.30});home.addEventListener('pointerleave',()=>pointer=0);
renderer.setAnimationLoop(ms=>{if(document.hidden)return;const t=ms/1000,elapsed=t-bowStart;let bend=0;if(!reduced&&elapsed>=0&&elapsed<4.8){if(elapsed<1.5)bend=(1-Math.cos(elapsed/1.5*Math.PI))/2;else if(elapsed<2.8)bend=1;else bend=(1+Math.cos((elapsed-2.8)/2*Math.PI))/2;}upper.rotation.x=bend*.64;head.rotation.x=bend*.12;rig.rotation.y+=( (dialog.open?0:-.11+pointer)-rig.rotation.y)*.035;rig.position.y=reduced?0:Math.sin(t*1.5)*.009;petals.forEach(p=>{if(reduced)return;const a=p.userData;p.position.y=a.y+Math.sin(t*.5+a.phase)*.1;p.position.x=a.x+Math.sin(t*.3+a.phase)*.08;p.rotation.y=t*.2+a.phase;});renderer.render(scene,camera);});
}catch(error){renderer?.dispose();throw error;}
return {show(){canvasParent=modalHost;modalHost.append(renderer.domElement);resize();bowStart=performance.now()/1000;},hide(){canvasParent=home;home.append(renderer.domElement);resize();},replay(){bowStart=performance.now()/1000;}};
}
