// Staggered scroll reveal
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('in');
      observer.unobserve(e.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

document.querySelectorAll('.reveal, .reveal-stagger').forEach(el => observer.observe(el));

// Subtle parallax on hero floating cards
const cards = document.querySelectorAll('.hero__visual .float-card');
if (cards.length && window.matchMedia('(min-width: 980px)').matches) {
  document.addEventListener('mousemove', (ev) => {
    const x = (ev.clientX / window.innerWidth - 0.5) * 2;
    const y = (ev.clientY / window.innerHeight - 0.5) * 2;
    cards.forEach((c, i) => {
      const depth = (i + 1) * 4;
      c.style.setProperty('--mx', `${x * depth}px`);
      c.style.setProperty('--my', `${y * depth}px`);
      c.style.transform = `translate(${x * depth}px, ${y * depth}px)`;
    });
  });
}
