/** Resolves once an intro's skip listeners are armed (SKIP_GRACE is 300ms in IntroStage). */
export const pastSkipGrace = () => new Promise<void>((resolve) => setTimeout(resolve, 350));
