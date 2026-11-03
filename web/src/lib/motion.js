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

const GROW_EASE = 'cubic-bezier(0.22, 0.61, 0.36, 1)';

export function grow(node, options) {
  let { value, key = '', delay = 0, property = 'width', duration = 900 } = options;
  let frame = 0;
  const still = () => prefersReducedMotion() || typeof requestAnimationFrame !== 'function';
  const show = (target) => {
    node.style[property] = `${target}%`;
  };
  const replay = () => {
    cancelAnimationFrame(frame);
    node.style.transition = 'none';
    show(0);
    frame = requestAnimationFrame(() => {
      frame = requestAnimationFrame(() => {
        node.style.transition = `${property} ${duration}ms ${GROW_EASE} ${delay}ms`;
        show(value);
      });
    });
  };
  if (still()) show(value);
  else replay();
  return {
    update(next) {
      const restart = (next.key ?? '') !== key;
      ({ value, key = '', delay = 0, property = 'width', duration = 900 } = next);
      if (still()) show(value);
      else if (restart) replay();
      else {
        node.style.transition = `${property} ${duration}ms ${GROW_EASE}`;
        show(value);
      }
    },
    destroy() {
      if (typeof cancelAnimationFrame === 'function') cancelAnimationFrame(frame);
    },
  };
}
