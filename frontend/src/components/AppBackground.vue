<template>
  <!-- Animated background layer — shown only for dark themes (v-if in App.vue).
       Non-scoped CSS because it consumes :root vars (--grid-line, --accent, ...)
       and shares keyframes globally. -->
  <div class="bg-layer">
    <div class="grid-bg"></div>
    <div class="scanline"></div>
    <div class="glow-orb orb-1"></div>
    <div class="glow-orb orb-2"></div>
  </div>
</template>

<script setup>
// Pure presentational — no logic.
</script>

<style>
.bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

.grid-bg {
  position: absolute;
  inset: -2px;
  background-image:
    linear-gradient(var(--grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: radial-gradient(ellipse at 50% 40%, #000 30%, transparent 85%);
  mask-image: radial-gradient(ellipse at 50% 40%, #000 30%, transparent 85%);
  animation: grid-pan 20s linear infinite;
}
@keyframes grid-pan {
  from { background-position: 0 0; }
  to { background-position: 44px 44px; }
}

.scanline {
  position: absolute;
  left: 0;
  right: 0;
  height: 120px;
  background: linear-gradient(180deg, transparent, var(--grid-line), transparent);
  animation: scan 6s linear infinite;
}
@keyframes scan {
  from { top: -120px; }
  to { top: 100%; }
}

.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.5;
}
.orb-1 {
  width: 360px;
  height: 360px;
  background: var(--accent);
  top: 10%;
  left: -80px;
  animation: float1 14s ease-in-out infinite;
}
.orb-2 {
  width: 420px;
  height: 420px;
  background: var(--accent2);
  bottom: 5%;
  right: -100px;
  animation: float2 18s ease-in-out infinite;
}
@keyframes float1 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(60px, 40px); }
}
@keyframes float2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-50px, -30px); }
}

/* deepspace variant: replace grid with a starfield */
[data-theme="deepspace"] .grid-bg {
  background-image:
    radial-gradient(1px 1px at 20% 30%, #fff, transparent),
    radial-gradient(1px 1px at 60% 70%, #fff, transparent),
    radial-gradient(1px 1px at 80% 20%, #cfe, transparent),
    radial-gradient(1px 1px at 35% 85%, #fff, transparent),
    radial-gradient(1px 1px at 90% 55%, #aef, transparent),
    linear-gradient(var(--grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
  background-size:
    200px 200px, 240px 240px, 180px 180px, 300px 300px, 220px 220px,
    60px 60px, 60px 60px;
}
</style>
