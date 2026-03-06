/**
 * Viperball Score Ticker Sketch
 *
 * Animated score display that counts up from 0 to the final score
 * with particle bursts on completion. Instance mode P5.js.
 *
 * Expects a global `_vbScoreData` object:
 *   { home: { name, score, color }, away: { name, score, color } }
 */

const viperballScoreTicker = (p) => {
  let homeScore = 0, awayScore = 0;
  let homeTarget = 0, awayTarget = 0;
  let homeName = '', awayName = '';
  let canvasW, canvasH;
  let animDone = false;
  const sparks = [];
  const ANIM_SPEED = 0.6;

  class Spark {
    constructor(x, y, col) {
      this.x = x;
      this.y = y;
      this.vx = p.random(-3, 3);
      this.vy = p.random(-4, -1);
      this.life = 1.0;
      this.decay = p.random(0.015, 0.035);
      this.size = p.random(3, 7);
      this.col = col;
    }
    update() {
      this.x += this.vx;
      this.vy += 0.08;
      this.y += this.vy;
      this.life -= this.decay;
    }
    draw() {
      if (this.life <= 0) return;
      p.noStroke();
      p.fill(this.col[0], this.col[1], this.col[2], this.life * 200);
      p.ellipse(this.x, this.y, this.size);
    }
    dead() { return this.life <= 0; }
  }

  function emitSparks(x, y, col, count) {
    for (let i = 0; i < count; i++) {
      sparks.push(new Spark(x, y, col));
    }
  }

  p.setup = () => {
    const container = document.getElementById('vb-score-ticker');
    if (!container) return;

    const data = window._vbScoreData || {};
    homeTarget = (data.home && data.home.score) || 0;
    awayTarget = (data.away && data.away.score) || 0;
    homeName = (data.home && data.home.name) || 'Home';
    awayName = (data.away && data.away.name) || 'Away';

    canvasW = container.offsetWidth;
    canvasH = 120;

    const canvas = p.createCanvas(canvasW, canvasH);
    canvas.parent('vb-score-ticker');
    p.textAlign(p.CENTER, p.CENTER);
    p.frameRate(60);
  };

  p.draw = () => {
    p.clear();

    /* Animate scores toward targets */
    let justFinishedHome = false, justFinishedAway = false;
    if (homeScore < homeTarget) {
      homeScore = p.min(homeScore + ANIM_SPEED, homeTarget);
      if (homeScore >= homeTarget) justFinishedHome = true;
    }
    if (awayScore < awayTarget) {
      awayScore = p.min(awayScore + ANIM_SPEED, awayTarget);
      if (awayScore >= awayTarget) justFinishedAway = true;
    }

    const midX = canvasW / 2;
    const scoreY = canvasH * 0.45;
    const nameY = canvasH * 0.82;

    /* "vs" divider */
    p.noStroke();
    p.fill(148, 163, 184, 120);
    p.textSize(14);
    p.textStyle(p.NORMAL);
    p.text('vs', midX, scoreY);

    /* Home score (left) */
    p.fill(79, 70, 229);
    p.textSize(52);
    p.textStyle(p.BOLD);
    p.text(p.floor(homeScore).toString(), midX - canvasW * 0.22, scoreY);

    /* Away score (right) */
    p.fill(99, 102, 241);
    p.textSize(52);
    p.text(p.floor(awayScore).toString(), midX + canvasW * 0.22, scoreY);

    /* Team names */
    p.fill(71, 85, 105);
    p.textSize(13);
    p.textStyle(p.BOLD);
    p.text(homeName, midX - canvasW * 0.22, nameY);
    p.text(awayName, midX + canvasW * 0.22, nameY);

    /* Spark on completion */
    if (justFinishedHome) emitSparks(midX - canvasW * 0.22, scoreY, [99, 102, 241], 25);
    if (justFinishedAway) emitSparks(midX + canvasW * 0.22, scoreY, [129, 140, 248], 25);

    /* Update / draw sparks */
    for (let i = sparks.length - 1; i >= 0; i--) {
      sparks[i].update();
      sparks[i].draw();
      if (sparks[i].dead()) sparks.splice(i, 1);
    }

    /* Subtle glow line at bottom */
    if (homeScore >= homeTarget && awayScore >= awayTarget && !animDone) {
      animDone = true;
    }
    if (animDone) {
      const glow = p.sin(p.frameCount * 0.03) * 30 + 40;
      p.stroke(99, 102, 241, glow);
      p.strokeWeight(1.5);
      p.line(midX - canvasW * 0.35, canvasH - 4, midX + canvasW * 0.35, canvasH - 4);
    }
  };

  p.windowResized = () => {
    const container = document.getElementById('vb-score-ticker');
    if (!container) return;
    canvasW = container.offsetWidth;
    p.resizeCanvas(canvasW, canvasH);
  };
};

/* Auto-launch when container exists */
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('vb-score-ticker')) {
    new p5(viperballScoreTicker);
  }
});
