/**
 * Viperball Ambient Background Sketch
 *
 * A subtle, slow-moving generative pattern using translucent geometric shapes
 * that drifts behind the page content, giving the site a premium dynamic feel.
 *
 * Uses P5.js instance mode so it doesn't pollute the global scope.
 */

const viperballAmbient = (p) => {
  const particles = [];
  const NUM_PARTICLES = 35;
  let canvasW, canvasH;

  /* Viperball palette — indigo/slate tones matching the existing CSS */
  const PALETTE = [
    [99, 102, 241, 18],   // indigo-500
    [129, 140, 248, 14],  // indigo-400
    [148, 163, 184, 12],  // slate-400
    [79, 70, 229, 10],    // indigo-600
    [165, 180, 252, 15],  // indigo-300
  ];

  class Particle {
    constructor() {
      this.reset();
    }

    reset() {
      this.x = p.random(canvasW || p.windowWidth);
      this.y = p.random(canvasH || p.windowHeight);
      this.size = p.random(40, 180);
      this.vx = p.random(-0.15, 0.15);
      this.vy = p.random(-0.08, 0.08);
      this.rotation = p.random(p.TWO_PI);
      this.rotSpeed = p.random(-0.002, 0.002);
      this.sides = p.floor(p.random(3, 7));
      this.color = PALETTE[p.floor(p.random(PALETTE.length))];
      this.pulseOffset = p.random(p.TWO_PI);
      this.pulseSpeed = p.random(0.005, 0.015);
    }

    update() {
      this.x += this.vx;
      this.y += this.vy;
      this.rotation += this.rotSpeed;

      /* Wrap around edges with padding */
      const pad = this.size;
      if (this.x < -pad) this.x = canvasW + pad;
      if (this.x > canvasW + pad) this.x = -pad;
      if (this.y < -pad) this.y = canvasH + pad;
      if (this.y > canvasH + pad) this.y = -pad;
    }

    draw() {
      const pulse = p.sin(p.frameCount * this.pulseSpeed + this.pulseOffset);
      const alpha = this.color[3] + pulse * 4;
      const sz = this.size + pulse * 8;

      p.push();
      p.translate(this.x, this.y);
      p.rotate(this.rotation);
      p.noStroke();
      p.fill(this.color[0], this.color[1], this.color[2], alpha);
      p.beginShape();
      for (let i = 0; i < this.sides; i++) {
        const angle = (p.TWO_PI / this.sides) * i - p.HALF_PI;
        p.vertex(p.cos(angle) * sz / 2, p.sin(angle) * sz / 2);
      }
      p.endShape(p.CLOSE);
      p.pop();
    }
  }

  p.setup = () => {
    const container = document.getElementById('vb-ambient-bg');
    if (!container) return;

    canvasW = container.offsetWidth;
    canvasH = container.offsetHeight;

    const canvas = p.createCanvas(canvasW, canvasH);
    canvas.parent('vb-ambient-bg');
    p.frameRate(15);

    for (let i = 0; i < NUM_PARTICLES; i++) {
      particles.push(new Particle());
    }

    /* Pause when tab is not visible to save CPU/GPU */
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) { p.noLoop(); } else { p.loop(); }
    });
  };

  p.draw = () => {
    p.clear();
    for (const pt of particles) {
      pt.update();
      pt.draw();
    }
  };

  p.windowResized = () => {
    const container = document.getElementById('vb-ambient-bg');
    if (!container) return;
    canvasW = container.offsetWidth;
    canvasH = container.offsetHeight;
    p.resizeCanvas(canvasW, canvasH);
  };
};

/* Wait for both P5.js (defer-loaded) and the container div (NiceGUI-rendered) */
(function _initAmbient() {
  if (typeof p5 === 'undefined' || !document.getElementById('vb-ambient-bg')) {
    setTimeout(_initAmbient, 100);
    return;
  }
  new p5(viperballAmbient);
})();
