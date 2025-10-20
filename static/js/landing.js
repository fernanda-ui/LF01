const hero = document.getElementById('hero');
const video = hero.querySelector('video');
const text = document.getElementById('heroText');
const emergingBox = document.getElementById('emergingBox');
const bottomBar = document.querySelector('.bottom-bar');

function clamp(v, a = 0, b = 1) {
  return Math.max(a, Math.min(b, v));
}

let lastExtendedProgress = 0;

window.addEventListener('scroll', () => {
  const scrollY = window.scrollY;

  // ---- PRIMERA FASE ----
  const maxScroll = window.innerHeight / 5;
  const progress = clamp(scrollY / maxScroll, 0, 1);

  const width = 85 - progress * 70; // 85 → 15vw
  const height = 80 - progress * 65; // 80 → 15vh
  const borderRadius = 4 + progress * 20;
  const r = Math.floor(progress * 255);
  const g = Math.floor((1 - progress) * 30);
  const b = Math.floor((1 - progress) * 40);
  const heroColor = `rgb(${r}, ${g}, ${b})`;

  const gray = Math.floor(progress * 180);
  const bodyColor = `rgb(${gray}, ${gray}, ${gray})`;
  const fontSize = 7 - progress * 4;

  hero.style.width = `${width}vw`;
  hero.style.height = `${height}vh`;
  hero.style.borderRadius = `${borderRadius}vh`;
  hero.style.background = heroColor;
  document.body.style.backgroundColor = bodyColor;
  video.style.opacity = `${1 - progress}`;
  text.style.color = progress < 0.8 ? '#ff2a2a' : '#ffffff';
  text.style.fontSize = `${fontSize}rem`;
  text.style.transform = `translate(-50%, -50%)`; // centrado perfecto

  // ---- SEGUNDA FASE ----
  const extendedStart = maxScroll;
  const extendedRange = window.innerHeight * 0.7;
  const extendedProgress = clamp((scrollY - extendedStart) / extendedRange, 0, 1);
  const smoothProgress = lastExtendedProgress + (extendedProgress - lastExtendedProgress) * 0.2;
  lastExtendedProgress = smoothProgress;

  // IRIS permanece centrado todo el tiempo (sin moverse hacia arriba)
  text.style.transform = 'translate(-50%, -50%)';

  // Solo se desvanece sin movimiento
  const irisOpacity = 1 - smoothProgress * 1.5;
  text.style.opacity = `${clamp(irisOpacity)}`;

  // ---- TERCERA FASE ----
  if (smoothProgress > 0.7) {
    const growProgress = (smoothProgress - 0.7) / 0.1;
    const grow = clamp(growProgress, 0, 1);

    // Más corto de ancho y un poco más alto
    hero.style.width = `${15 + grow * 15}vw`;  // 15vw → 30vw (más corto)
    hero.style.height = `${10}vh`;             // un poco más alto
    hero.style.borderRadius = "9999px";        // forma ovalada suave
  } else {
    hero.style.width = `${15}vw`;
    hero.style.height = `${10}vh`;
    hero.style.borderRadius = "9999px";
  }

  // ---- CUARTA FASE ----
  if (smoothProgress > 0.8) {
    emergingBox.classList.add('visible');
  } else {
    emergingBox.classList.remove('visible');
  }

  // ---- RESTAURAR AL SUBIR ----
  if (scrollY < extendedStart) {
    hero.style.width = `90vw`;
    hero.style.height = `85vh`;
    hero.style.borderRadius = `4vh`;
    text.style.opacity = `1`;
    text.style.transform = `translate(-50%, -50%)`;
    emergingBox.classList.remove('visible');
  }

  // ---- OCULTAR BARRA INFERIOR ----
  const maxScrollBar = window.innerHeight * 0.6;
  bottomBar.classList.toggle('hidden', scrollY > maxScrollBar);
});

// ---- ANIMACIÓN INICIAL ----
window.addEventListener('load', () => {
  hero.style.width = "15vw";
  hero.style.height = "15vh";
  hero.style.borderRadius = "24vh";
  hero.style.background = "rgba(73, 10, 10, 1)";
  hero.style.transition = "all 3s cubic-bezier(0.25, 1, 0.3, 1)";
  hero.style.transform = "translate(-50%, -50%)";

  text.style.color = "#ffffff";
  text.style.fontSize = "4rem";
  text.style.opacity = "0";
  text.style.transform = "translate(-50%, -50%)";
  text.style.transition = "opacity 1.2s ease, color 2s ease, font-size 2s ease";

  video.style.opacity = "0";
  video.style.transition = "opacity 2s ease 1.8s";

  document.body.style.backgroundColor = "rgb(180,180,180)";
  document.body.style.transition = "background-color 2s ease";

  setTimeout(() => text.style.opacity = "1", 400);

  setTimeout(() => {
    hero.style.transition = "all 3s cubic-bezier(0.4, 0, 0.2, 1)";
    text.style.transition = "color 2s ease, font-size 2s ease";
    hero.style.width = "90vw";
    hero.style.height = "85vh";
    hero.style.borderRadius = "4vh";
    hero.style.background = "linear-gradient(180deg, #2a0205ff, #111)";
    document.body.style.backgroundColor = "#0f0a0aff";
    video.style.opacity = "1";
    text.style.color = "#5f0303ff";
    text.style.fontSize = "7rem";
  }, 2000);
});


// ---- EFECTO DE MÁQUINA DE ESCRIBIR CONTROLADO POR SCROLL ----
const prepText = document.getElementById("prepText");
let typingStarted = false;

const message = "¿Preparado para usar a IRIS?";
let charIndex = 0;
let deleting = false;

function typeEffect() {
  const visibleText = message.substring(0, charIndex);
  prepText.textContent = visibleText;

  if (!deleting && charIndex < message.length) {
    charIndex++;
    setTimeout(typeEffect, 100);
  } else if (deleting && charIndex > 0) {
    charIndex--;
    setTimeout(typeEffect, 60);
  } else {
    deleting = !deleting;
    setTimeout(typeEffect, deleting ? 1500 : 500);
  }
}

// Activar animación cuando el texto aparezca en pantalla
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting && !typingStarted) {
      typingStarted = true;
      typeEffect();
    }
  });
}, { threshold: 0.5 });

observer.observe(prepText);


window.addEventListener('beforeunload', () => window.scrollTo(0, 0));


