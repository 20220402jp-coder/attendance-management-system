import * as THREE from './vendor/three.module.js';
export function mountCyber(host){
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.setClearColor(0,0);host.append(renderer.domElement);
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(39,1,.1,30);camera.position.set(0,0,6.3);
 const assembly=new THREE.Group();scene.add(assembly);
 const cyan=new THREE.MeshBasicMaterial({color:'#53e9e2',transparent:true,opacity:.72}),dim=new THREE.MeshBasicMaterial({color:'#22728b',transparent:true,opacity:.38}),violet=new THREE.MeshBasicMaterial({color:'#7b8ded',transparent:true,opacity:.5});
 function ring(radius,tube,material,arc=Math.PI*2){const m=new THREE.Mesh(new THREE.TorusGeometry(radius,tube,8,128,arc),material);assembly.add(m);return m;}
 const outer=ring(1.62,.022,cyan,Math.PI*1.35);outer.rotation.z=.5;const inner=ring(1.43,.009,dim);inner.rotation.x=.23;const middle=ring(1.53,.009,violet,Math.PI*1.5);middle.rotation.y=-.23;ring(1.79,.005,dim);
 const ticks=new THREE.Group();assembly.add(ticks);for(let i=0;i<64;i++){const a=i/64*Math.PI*2,major=i%8===0;const m=new THREE.Mesh(new THREE.BoxGeometry(major?.018:.009,major?.12:.035,.024),major?cyan:dim);m.position.set(Math.sin(a)*1.71,Math.cos(a)*1.71,Math.sin(a*2)*.06);m.rotation.z=-a;ticks.add(m);}
 const points=[];for(let i=0;i<80;i++){const a=i*2.39996,r=1.94+(i%7)*.12;points.push(Math.cos(a)*r,Math.sin(a)*r,Math.sin(i)*.65);}const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(points,3));const particles=new THREE.Points(geometry,new THREE.PointsMaterial({color:'#68bdde',size:.024,transparent:true,opacity:.5}));scene.add(particles);
 const nodes=new THREE.Group();assembly.add(nodes);for(let i=0;i<4;i++){const a=i*Math.PI/2+.2;const n=new THREE.Mesh(new THREE.OctahedronGeometry(.05),cyan);n.position.set(Math.cos(a)*1.88,Math.sin(a)*1.88,.1);nodes.add(n);}
 function resize(){const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}const observer=new ResizeObserver(resize);observer.observe(host);resize();let px=0,py=0;const panel=host.parentElement;panel.addEventListener('pointermove',e=>{const r=panel.getBoundingClientRect();px=((e.clientX-r.left)/r.width-.5)*.3;py=((e.clientY-r.top)/r.height-.5)*.25;});panel.addEventListener('pointerleave',()=>{px=py=0;});
 renderer.setAnimationLoop(ms=>{if(document.hidden)return;const t=ms*.001;if(!reduced){outer.rotation.z=t*.08;middle.rotation.z=-t*.12;nodes.rotation.z=t*.045;particles.rotation.z=-t*.009;assembly.rotation.y+=(px-assembly.rotation.y)*.035;assembly.rotation.x+=(-py-assembly.rotation.x)*.035;}renderer.render(scene,camera);});
 host.dataset.ready='true';host.parentElement.classList.add('has-webgl');
 host.addEventListener('webglcontextlost',()=>panel.classList.remove('has-webgl'),true);
 return ()=>{renderer.setAnimationLoop(null);observer.disconnect();scene.traverse(o=>o.geometry?.dispose());[cyan,dim,violet,particles.material].forEach(m=>m.dispose());renderer.dispose();};
}
