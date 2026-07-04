/* =========================================================================
   VoiceOrb — a dependency-free, audio-reactive orb for voice-agent UIs.
   Canvas-based. No external assets, no build step.

   Usage:
     import { VoiceOrb } from './voice-orb.js';

     const orb = new VoiceOrb(document.getElementById('orb-container'));
     orb.setState('listening');   // 'idle' | 'listening' | 'speaking' | 'thinking' | 'error'
     orb.setLevel(0.6);           // 0..1, feed from your audio amplitude/RMS
     orb.onStateChange(state => console.log('now', state));
     orb.destroy();               // stop animation loop, release observers

   Markup it expects:
     <div id="orb-container"><canvas></canvas></div>
     (a canvas will be created for you if the container is empty)
   ========================================================================= */

const THEMES = {
  idle:      { a: '#4f7cff', b: '#6d5cff', c: '#9b5cff' }, // cool, at rest
  listening: { a: '#33c7ff', b: '#4f9bff', c: '#5c7dff' }, // alert, cyan-forward
  speaking:  { a: '#ff5c9d', b: '#ff6f4f', c: '#ffb454' }, // energetic, warm
  thinking:  { a: '#6d5cff', b: '#9b5cff', c: '#c15cff' }, // contemplative, violet
  error:     { a: '#ff5c5c', b: '#ff8a3d', c: '#ffb454' }, // caution, amber-red
};

const VALID_STATES = Object.keys(THEMES);

export class VoiceOrb {
  constructor(container, opts = {}) {
    this.container = container;
    this.canvas = container.querySelector('canvas') || document.createElement('canvas');
    if (!this.canvas.parentNode) container.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');

    this.highlight = opts.highlightColor || 'rgba(255,255,255,0.55)';
    this.themes = Object.assign({}, THEMES, opts.themeOverrides || {});

    this.state = 'idle';
    this.level = 0;
    this._smoothLevel = 0;
    this.t = 0;
    this._particles = [];
    this._listeners = new Set();

    // current rendered color (lerped toward the target theme every frame,
    // so switching states crossfades instead of snapping)
    this._color = { ...this.themes.idle };
    this._targetColor = { ...this.themes.idle };

    this._reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this._motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    this._onMotionChange = (e) => { this._reducedMotion = e.matches; };
    this._motionQuery.addEventListener('change', this._onMotionChange);

    this._resize();
    this._ro = new ResizeObserver(() => this._resize());
    this._ro.observe(this.container);

    this._raf = requestAnimationFrame((ts) => this._loop(ts));
  }

  /** Switch visual/behavioral state. Colors crossfade over ~500ms. */
  setState(state) {
    if (!VALID_STATES.includes(state) || state === this.state) return;
    this.state = state;
    this._targetColor = { ...this.themes[state] };
    this._listeners.forEach((fn) => fn(state));
  }

  /** Feed instantaneous audio level, 0..1 (e.g. RMS or frequency-bin average). */
  setLevel(level) {
    this.level = Math.max(0, Math.min(1, level));
  }

  getState() {
    return this.state;
  }

  /** Register a callback fired whenever setState changes the state. Returns an unsubscribe fn. */
  onStateChange(fn) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }

  destroy() {
    cancelAnimationFrame(this._raf);
    this._ro.disconnect();
    this._motionQuery.removeEventListener('change', this._onMotionChange);
  }

  // ---- internals ----------------------------------------------------------

  _resize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.container.getBoundingClientRect();
    this.size = Math.min(rect.width, rect.height) || 220;
    this.canvas.width = this.size * dpr;
    this.canvas.height = this.size * dpr;
    this.canvas.style.width = this.size + 'px';
    this.canvas.style.height = this.size + 'px';
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  _noise(x) {
    const s = Math.sin(x * 12.9898) * 43758.5453;
    return s - Math.floor(s);
  }
  _smoothNoise(x) {
    const i = Math.floor(x);
    const f = x - i;
    const a = this._noise(i);
    const b = this._noise(i + 1);
    const u = f * f * (3 - 2 * f);
    return a + (b - a) * u;
  }

  _lerpColor() {
    const rate = 0.06;
    for (const k of ['a', 'b', 'c']) {
      const cur = this._hexToRgb(this._color[k]);
      const tgt = this._hexToRgb(this._targetColor[k]);
      const r = cur.r + (tgt.r - cur.r) * rate;
      const g = cur.g + (tgt.g - cur.g) * rate;
      const b = cur.b + (tgt.b - cur.b) * rate;
      this._color[k] = this._rgbToHex(r, g, b);
    }
  }

  _loop(ts) {
    this.t = ts / 1000;
    this._lerpColor();
    this._draw();
    this._raf = requestAnimationFrame((ts2) => this._loop(ts2));
  }

  _draw() {
    const { ctx, size, t, state } = this;
    ctx.clearRect(0, 0, size, size);

    const cx = size / 2, cy = size / 2;
    const baseR = size * 0.28;
    const motion = this._reducedMotion ? 0.25 : 1; // dampen everything if requested

    let targetLevel = this.level;
    let speed = 1;

    if (state === 'idle') {
      targetLevel = 0.12 + 0.05 * Math.sin(t * 1.2) * motion;
      speed = 0.4;
    } else if (state === 'listening') {
      speed = 1.1;
    } else if (state === 'speaking') {
      targetLevel = Math.max(this.level, 0.35 + 0.35 * Math.abs(Math.sin(t * 4.5)) * motion);
      speed = 1.8;
    } else if (state === 'thinking') {
      targetLevel = 0.18;
      speed = 0.9;
    } else if (state === 'error') {
      targetLevel = 0.2 + 0.1 * Math.abs(Math.sin(t * 3)) * motion;
      speed = 0.6;
    }
    speed *= motion || 1;
    if (this._reducedMotion) speed = Math.min(speed, 0.3);

    this._smoothLevel += (targetLevel - this._smoothLevel) * 0.12;
    const level = this._smoothLevel;
    const radius = baseR * (1 + level * 0.55);
    const { a, b, c } = this._color;

    // --- outer glow ---
    const glowR = radius * (2.2 + level * 0.6);
    const glow = ctx.createRadialGradient(cx, cy, radius * 0.4, cx, cy, glowR);
    glow.addColorStop(0, this._hexA(b, 0.35 + level * 0.25));
    glow.addColorStop(1, this._hexA(b, 0));
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(cx, cy, glowR, 0, Math.PI * 2);
    ctx.fill();

    // --- rotating processing ring (thinking) ---
    if (state === 'thinking') {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(t * 1.6 * motion);
      const ringR = radius * 1.35;
      const grad = ctx.createLinearGradient(-ringR, 0, ringR, 0);
      grad.addColorStop(0, this._hexA(a, 0));
      grad.addColorStop(0.5, this._hexA(a, 0.8));
      grad.addColorStop(1, this._hexA(a, 0));
      ctx.strokeStyle = grad;
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(0, 0, ringR, 0, Math.PI * 1.4);
      ctx.stroke();
      ctx.restore();
    }

    // --- listening ripple rings ---
    if (state === 'listening' && level > 0.15) {
      for (let i = 0; i < 2; i++) {
        const phase = (t * 0.9 * motion + i * 0.5) % 1;
        const r = radius * (1 + phase * 1.1);
        const alpha = (1 - phase) * 0.25 * (0.4 + level);
        ctx.strokeStyle = this._hexA(a, alpha);
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    // --- error pulse ring ---
    if (state === 'error') {
      const pulse = 0.5 + 0.5 * Math.sin(t * 4);
      ctx.strokeStyle = this._hexA(a, 0.3 + pulse * 0.3);
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.2, 0, Math.PI * 2);
      ctx.stroke();
    }

    // --- speaking accent particles (bursting outward with level) ---
    if (state === 'speaking') {
      this._updateParticles(cx, cy, radius, level);
      for (const p of this._particles) {
        ctx.fillStyle = this._hexA(c, p.life);
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (this._particles.length) {
      this._particles.length = 0;
    }

    // --- core blob: two offset noise layers for a sense of depth ---
    this._drawBlobLayer(cx, cy, radius, t, speed, level, 48, 1.0, 0.16, [a, b, c]);
    this._drawBlobLayer(cx, cy, radius * 0.86, t, speed * 1.3, level, 40, -0.7, 0.1, [b, c, a], 0.55);

    // --- specular highlight (glass feel) ---
    const hl = ctx.createRadialGradient(
      cx - radius * 0.35, cy - radius * 0.4, 0,
      cx - radius * 0.35, cy - radius * 0.4, radius * 0.6
    );
    hl.addColorStop(0, this.highlight);
    hl.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = hl;
    ctx.beginPath();
    ctx.arc(cx - radius * 0.3, cy - radius * 0.35, radius * 0.55, 0, Math.PI * 2);
    ctx.fill();
  }

  _drawBlobLayer(cx, cy, radius, t, speed, level, points, phaseDir, ampScale, colors, alpha = 1) {
    const ctx = this.ctx;
    const distortAmp = radius * (0.05 + level * ampScale);
    ctx.beginPath();
    for (let i = 0; i <= points; i++) {
      const theta = (i / points) * Math.PI * 2;
      const n = this._smoothNoise(theta * 2.1 + t * speed * 0.6 * phaseDir) - 0.5;
      const r = radius + n * distortAmp;
      const x = cx + Math.cos(theta) * r;
      const y = cy + Math.sin(theta) * r;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();

    const [c1, c2, c3] = colors;
    const grad = ctx.createRadialGradient(
      cx - radius * 0.3, cy - radius * 0.35, radius * 0.1,
      cx, cy, radius * 1.1
    );
    grad.addColorStop(0, c1);
    grad.addColorStop(0.55, c2);
    grad.addColorStop(1, c3);
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.restore();
  }

  _updateParticles(cx, cy, radius, level) {
    // spawn rate scales with level; particles drift outward and fade
    if (Math.random() < level * 0.9) {
      const theta = Math.random() * Math.PI * 2;
      this._particles.push({
        x: cx + Math.cos(theta) * radius * 0.9,
        y: cy + Math.sin(theta) * radius * 0.9,
        vx: Math.cos(theta) * (0.6 + level * 1.2),
        vy: Math.sin(theta) * (0.6 + level * 1.2),
        r: 1.5 + Math.random() * 2,
        life: 1,
      });
    }
    for (const p of this._particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.life -= 0.02;
    }
    this._particles = this._particles.filter((p) => p.life > 0).slice(-40);
  }

  _hexToRgb(hex) {
    const c = hex.replace('#', '');
    return {
      r: parseInt(c.substring(0, 2), 16),
      g: parseInt(c.substring(2, 4), 16),
      b: parseInt(c.substring(4, 6), 16),
    };
  }
  _rgbToHex(r, g, b) {
    const toHex = (v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0');
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
  }
  _hexA(hex, alpha) {
    const { r, g, b } = this._hexToRgb(hex);
    return `rgba(${r},${g},${b},${alpha})`;
  }
}

/* -------------------------------------------------------------------------
   Optional: wire the orb to a real microphone using the Web Audio API.
   Call connectMic(orb) after a user gesture (mic access requires one).
   ------------------------------------------------------------------------- */
export async function connectMic(orb) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioCtx.createMediaStreamSource(stream);
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 512;
  source.connect(analyser);
  const data = new Uint8Array(analyser.frequencyBinCount);

  let raf;
  function tick() {
    analyser.getByteFrequencyData(data);
    const avg = data.reduce((sum, v) => sum + v, 0) / data.length;
    orb.setLevel(avg / 255);
    raf = requestAnimationFrame(tick);
  }
  tick();

  return () => {
    cancelAnimationFrame(raf);
    stream.getTracks().forEach((tr) => tr.stop());
    audioCtx.close();
  };
}