/** Deterministic fixture; no secrets or external HTTP requests. */
export function add(left, right) {
  if (!Number.isFinite(left) || !Number.isFinite(right)) {
    throw new TypeError('Only finite numbers can be added');
  }
  return left + right;
}
