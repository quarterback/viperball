/**
 * Viperball Nav Glow
 *
 * A thin canvas strip that sits under the header, rendering a
 * slowly shifting gradient glow line that responds to mouse position.
 * Gives the nav bar a premium, living feel.
 */

const viperballNavGlow = (p) => {
  let canvasW, canvasH;
  const GLOW_HEIGHT = 3;

  p.setup = () => {
    const container = document.getElementById('vb-nav-glow');
    if (!container) return;
    canvasW = container.offsetWidth;
    canvasH = GLOW_HEIGHT;
    const canvas = p.createCanvas(canvasW, canvasH);
    canvas.parent('vb-nav-glow');
    p.noStroke();
    p.frameRate(30);
  };

  p.draw = () => {
    p.clear();
    const t = p.frameCount * 0.01;
    const mouseRatio = p.mouseX / (canvasW || 1);

    for (let x = 0; x < canvasW; x += 2) {
      const ratio = x / canvasW;
      /* Combine time-based drift with mouse proximity */
      const dist = p.abs(ratio - mouseRatio);
      const mouseBright = p.max(0, 1 - dist * 3);
      const wave = p.sin(ratio * 6 + t) * 0.5 + 0.5;
      const alpha = (wave * 35 + mouseBright * 80);

      /* Shift hue along the bar: indigo to violet */
      const r = p.lerp(79, 139, ratio + p.sin(t + ratio * 3) * 0.2);
      const g = p.lerp(70, 92, ratio);
      const b = p.lerp(229, 246, p.sin(t * 0.7 + ratio * 2) * 0.5 + 0.5);

      p.fill(r, g, b, alpha);
      p.rect(x, 0, 3, canvasH);
    }
  };

  p.windowResized = () => {
    const container = document.getElementById('vb-nav-glow');
    if (!container) return;
    canvasW = container.offsetWidth;
    p.resizeCanvas(canvasW, canvasH);
  };
};

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('vb-nav-glow')) {
    new p5(viperballNavGlow);
  }
});
