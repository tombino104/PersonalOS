export function prefersReducedMotion() {
  return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function playProgress(onFrame, { duration = 1400, delay = 0 } = {}) {
  if (prefersReducedMotion() || typeof requestAnimationFrame !== 'function') {
    onFrame(1);
    return () => {};
  }
  onFrame(0);
  const begin = performance.now() + delay;
  let frame = 0;
  const step = (now) => {
    const progress = Math.min(1, Math.max(0, (now - begin) / duration));
    onFrame(progress);
    if (progress < 1) frame = requestAnimationFrame(step);
  };
  frame = requestAnimationFrame(step);
  return () => cancelAnimationFrame(frame);
}
