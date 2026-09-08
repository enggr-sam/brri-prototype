/** Client-side path change without a full reload. */
export function goTo(path) {
  if (window.location.pathname === path && !window.location.hash) return;
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function handleAppLink(event, path) {
  if (
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return;
  }
  event.preventDefault();
  goTo(path);
}
