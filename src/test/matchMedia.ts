function install(matchesFor: (query: string) => boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: matchesFor(query),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

/** Makes matchMedia report `matches` for exactly this query (false for others). */
export function mockMatchMedia(query: string, matches: boolean) {
  install((q) => q === query && matches);
}

export function resetMatchMedia() {
  install(() => false);
}
