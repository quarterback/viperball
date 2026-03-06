/**
 * Viperball Page Transition Effect
 *
 * When triggered, plays a quick wipe/dissolve animation overlay.
 * Call window.vbTransition() to trigger the animation.
 */

const viperballPageTransition = (p) => {
  let canvasW, canvasH;
  let active = false;
  let progress = 0;
  const SPEED = 0.06;
  const dots = [];

  p.setup = () => {
    const container = document.getElementById('vb-page-transition');
    if (!container) return;
    canvasW = p.windowWidth;
    canvasH = p.windowHeight;
    const canvas = p.createCanvas(canvasW, canvasH);
    canvas.parent('vb-page-transition');
    p.noStroke();
    p.frameRate(60);

    /* Expose trigger function globally */
    window.vbTransition = () => {
      active = true;
      progress = 0;
      dots.length = 0;
      for (let i = 0; i < 60; i++) {
        dots.push({
          x: p.random(canvasW),
          y: p.random(canvasH),
          size: p.random(4, 20),
          speed: p.random(0.02, 0.06),
          delay: p.random(0, 0.3),
        });
      }
    };
  };

  p.draw = () => {
    p.clear();
    if (!active) return;

    progress += SPEED;

    for (const d of dots) {
      const t = p.max(0, progress - d.delay);
      if (t <= 0) continue;
      /* Fade in then out */
      const alpha = t < 0.5 ? t * 2 : p.max(0, 2 - t * 2);
      const sz = d.size * (0.5 + t * 0.5);
      p.fill(99, 102, 241, alpha * 100);
      p.ellipse(d.x, d.y, sz);
    }

    if (progress > 2) {
      active = false;
    }
  };

  p.windowResized = () => {
    canvasW = p.windowWidth;
    canvasH = p.windowHeight;
    p.resizeCanvas(canvasW, canvasH);
  };
};

(function _initPageTransition() {
  if (typeof p5 === 'undefined' || !document.getElementById('vb-page-transition')) {
    setTimeout(_initPageTransition, 100);
    return;
  }
  new p5(viperballPageTransition);
})();
