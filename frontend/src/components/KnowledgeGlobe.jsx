import { useEffect, useRef } from 'react'
import * as THREE from 'three'
export default function KnowledgeGlobe({animate}){
 const mount=useRef(null),enabled=useRef(animate)
 useEffect(()=>{enabled.current=animate},[animate])
 useEffect(()=>{
  const el=mount.current;let renderer,frame
  try{renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'})}catch{el.classList.add('globe-fallback');return}
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(40,1,.1,100);camera.position.z=5.6
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.7));el.appendChild(renderer.domElement)
  const group=new THREE.Group();scene.add(group)
  group.add(new THREE.Mesh(new THREE.SphereGeometry(1.38,48,32),new THREE.MeshPhongMaterial({color:0x142333,transparent:true,opacity:.92,shininess:110})))
  scene.add(new THREE.AmbientLight(0xdac7a4,1.8));const light=new THREE.DirectionalLight(0xffdc9e,3);light.position.set(-3,4,3);scene.add(light)
  const rim=new THREE.PointLight(0x80a8c9,8,15);rim.position.set(3,-2,2);scene.add(rim)
  group.add(new THREE.LineSegments(new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(1.405,3)),new THREE.LineBasicMaterial({color:0xb9a076,transparent:true,opacity:.28})))
  const vertices=[];for(let i=0;i<370;i++){const y=1-(i/369)*2,r=Math.sqrt(1-y*y),phi=i*Math.PI*(3-Math.sqrt(5));vertices.push(1.43*Math.cos(phi)*r,1.43*y,1.43*Math.sin(phi)*r)}
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));group.add(new THREE.Points(geometry,new THREE.PointsMaterial({color:0xffde99,size:.025,transparent:true,opacity:.95})))
  for(let i=0;i<3;i++){const ring=new THREE.Mesh(new THREE.TorusGeometry(1.69+i*.14,.009,8,120),new THREE.MeshBasicMaterial({color:i===1?0xe6b764:0xffd795,transparent:true,opacity:.55}));ring.rotation.set(Math.PI/(2+i*.6),.4+i*.5,i*.5);scene.add(ring)}
  let pointerX=0,pointerY=0,visible=true
  const onPointer=e=>{const b=el.getBoundingClientRect();pointerX=(e.clientX-b.left)/b.width-.5;pointerY=(e.clientY-b.top)/b.height-.5};el.addEventListener('pointermove',onPointer)
  const resize=()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()};const observer=new ResizeObserver(resize);observer.observe(el);resize()
  const onVisibility=()=>{visible=!document.hidden};document.addEventListener('visibilitychange',onVisibility)
  const started=performance.now();function draw(){frame=requestAnimationFrame(draw);if(!visible)return;if(enabled.current){group.rotation.y+=.0018;group.rotation.x+=(pointerY*.15-group.rotation.x)*.025;camera.position.x+=(pointerX*.22-camera.position.x)*.025;camera.lookAt(0,0,0);group.position.y=Math.sin(((performance.now()-started)/1000)*.6)*.045}renderer.render(scene,camera)}draw()
  return()=>{cancelAnimationFrame(frame);observer.disconnect();el.removeEventListener('pointermove',onPointer);document.removeEventListener('visibilitychange',onVisibility);scene.traverse(o=>{o.geometry?.dispose();o.material?.dispose()});renderer.dispose();renderer.domElement.remove()}
 },[])
 return <div className="globe-canvas" ref={mount} aria-hidden="true"/>
}
