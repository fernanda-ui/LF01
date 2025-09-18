import * as THREE from 'https://cdn.skypack.dev/three@0.129.0/build/three.module.js';
import { GLTFLoader } from 'https://cdn.skypack.dev/three@0.129.0/examples/jsm/loaders/GLTFLoader.js';
import { gsap } from 'https://cdn.skypack.dev/gsap';

let leaf; 

const leafLoader = new GLTFLoader();
leafLoader.load('/static/neuron.glb', function (gltf) {
    leaf = gltf.scene;

    // Escala y posición de fondo
    leaf.scale.set(5, 5, 5);
    leaf.position.set(0, -2, -20);
    leaf.rotation.set(0.2, 0.5, 0);

    // Transparencia + tono claro
    leaf.traverse((child) => {
        if (child.isMesh) {
            child.material.transparent = true; 
            child.material.opacity = 0.4;
            child.material.color.set('#aaffcc');
        }
    });

    scene.add(leaf);
});

let isLeafVisible = false; 

window.addEventListener("scroll", () => {
    if (!leaf) return;

    const banner = document.getElementById("banner");
    const rect = banner.getBoundingClientRect();

    if (rect.bottom > 0 && rect.top < window.innerHeight) {
        if (!isLeafVisible) {
            isLeafVisible = true;
            gsap.to(leaf.scale, { x: 5, y: 5, z: 5, duration: 1, ease: "elastic.out(1, 0.5)" });
            gsap.to(leaf.rotation, { y: 0.5, duration: 1.2, ease: "power2.out" });
            gsap.to(leaf.position, { z: -20, opacity: 1, duration: 1 });
            gsap.to(leaf.traverse((child)=>{if(child.isMesh) child.material;}), {opacity: 0.4});
            leaf.visible = true;
        }
    } else {
        if (isLeafVisible) {
            isLeafVisible = false;
            // Animación de desaparición
            gsap.to(leaf.scale, { x: 0, y: 0, z: 0, duration: 1, ease: "back.in(1.5)" });
            gsap.to(leaf.rotation, { y: leaf.rotation.y + 1, duration: 1, ease: "power2.in" });
            gsap.to(leaf.position, { z: -30, duration: 1 });
            gsap.to(leaf.traverse((child)=>{if(child.isMesh) child.material;}), {opacity: 0});
            // Lo ocultamos tras animación
            setTimeout(() => { leaf.visible = false; }, 1000);
        }
    }
});



// TYPING EFFECT
const typingElement = document.getElementById("typing-text");

const phrases = [
  "Haz tus tareas del día a día en tu PC usando solo tu voz.",
  "Ordénale y pregúntale lo que quieras.",
  "Solo di «Iris» para pedir lo que necesites.",
  "Disfruta de su compañía y apariencia."
];

let phraseIndex = 0;
let charIndex = 0;
let isDeleting = false;

function typeEffect() {
  const currentPhrase = phrases[phraseIndex];
  
  if (!isDeleting) {
    // Escribiendo
    typingElement.textContent = currentPhrase.substring(0, charIndex + 1);
    charIndex++;
    if (charIndex === currentPhrase.length) {
      isDeleting = true;
      setTimeout(typeEffect, 2000); // pausa antes de borrar
      return;
    }
  } else {
    // Borrando
    typingElement.textContent = currentPhrase.substring(0, charIndex - 1);
    charIndex--;
    if (charIndex === 0) {
      isDeleting = false;
      phraseIndex = (phraseIndex + 1) % phrases.length;
    }
  }
  
  setTimeout(typeEffect, isDeleting ? 50 : 100);
}

// Iniciar efecto typing
typeEffect();




// CÁMARA
const camera = new THREE.PerspectiveCamera(
    10,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
);
camera.position.z = 10;

// ESCENA
const scene = new THREE.Scene();
let bee;
let mixer;
const loader = new GLTFLoader();
loader.load('/static/logo.glb',
    function (gltf) {
        bee = gltf.scene;

        // 🔹 Estado inicial de frente
        bee.rotation.y = 4.3;
        bee.position.y = 1;

        scene.add(bee);

        mixer = new THREE.AnimationMixer(bee);
        if (gltf.animations.length > 0) {
            mixer.clipAction(gltf.animations[0]).play();
        }

        modelMove();
    }
);

// RENDER
const renderer = new THREE.WebGLRenderer({ alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.getElementById('container3D').appendChild(renderer.domElement);

// LUCES
const ambientLight = new THREE.AmbientLight(0xffffff, 1.3);
scene.add(ambientLight);
const topLight = new THREE.DirectionalLight(0xffffff, 1);
topLight.position.set(500, 500, 500);
scene.add(topLight);

// BUCLE RENDER
const reRender3D = () => {
    requestAnimationFrame(reRender3D);
    renderer.render(scene, camera);
    if (mixer) mixer.update(0.02);
};
reRender3D();

// ANIMACIÓN DEPENDIENDO DEL SCROLL
const modelMove = () => {
    if (!bee) return;

    let scrollTop = window.scrollY;
    let maxScroll = document.body.scrollHeight - window.innerHeight;
    let progress = scrollTop / maxScroll; // entre 0 y 1

    // ROTACIÓN limitada: desde 4.3 (frente) hasta 4.3 + 1.5 rad (~85°)
    let targetRotationY = 4.3 + progress * 1.5;

    // Rebote suave: sube y baja un poquito
    let targetY = -0.6 + Math.sin(progress * Math.PI) * 0.3;

    gsap.to(bee.rotation, {
        y: targetRotationY,
        duration: 1,
        ease: "power2.out"
    });

    gsap.to(bee.position, {
        y: targetY,
        duration: 0.8,
        ease: "bounce.out"
    });
};

// EVENTOS
window.addEventListener('scroll', () => {
    modelMove();
});

window.addEventListener('resize', () => {
    renderer.setSize(window.innerWidth, window.innerHeight);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
});
