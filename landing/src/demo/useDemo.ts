import { useCallback, useEffect, useReducer, useState, type RefObject } from 'react'

/** The replica plays the app's real flow as four scenes. Each scene is drawn from `t`, the milliseconds spent in it,
 *  so a scene can be shown at any moment: playing, paused, or jumped to. */
export const SCENES = ['find', 'write', 'digest', 'download'] as const
export type Scene = (typeof SCENES)[number]

export const DURATION: Record<Scene, number> = { find: 4200, write: 6000, digest: 9000, download: 4800 }

const TICK = 100

export type DemoState = { scene: Scene; t: number; playing: boolean; finished: boolean }

export type DemoAction =
  | { type: 'tick'; ms: number }
  | { type: 'go'; scene: Scene }
  | { type: 'toggle' }
  | { type: 'pause' }

/** Reduced motion, or a visitor who arrives on a scene's link: the scene as it looks when finished, not playing. */
export function stillState(scene: Scene): DemoState {
  return { scene, t: DURATION[scene], playing: false, finished: false }
}

export const startState: DemoState = { scene: 'find', t: 0, playing: true, finished: false }

export function demoReducer(state: DemoState, action: DemoAction): DemoState {
  switch (action.type) {
    case 'tick': {
      if (!state.playing) return state
      const t = state.t + action.ms
      if (t < DURATION[state.scene]) return { ...state, t }
      const next = SCENES.indexOf(state.scene) + 1
      // It plays once and stops on the download, so nothing runs while nobody watches.
      if (next >= SCENES.length) return { ...state, t: DURATION[state.scene], playing: false, finished: true }
      return { ...state, scene: SCENES[next], t: 0 }
    }
    case 'go':
      // Jumping while it plays starts that scene; while paused, it shows the scene finished.
      return state.playing ? { ...state, scene: action.scene, t: 0, finished: false } : { ...stillState(action.scene) }
    case 'toggle':
      if (state.finished) return startState
      return { ...state, playing: !state.playing }
    case 'pause':
      return state.playing ? { ...state, playing: false } : state
  }
}

function sceneFromHash(): Scene | null {
  const match = /^#demo-(\w+)$/.exec(window.location.hash)
  return match && (SCENES as readonly string[]).includes(match[1]) ? (match[1] as Scene) : null
}

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Runs the replica: it only advances while it is on screen, not held (pointer or focus inside it) and not paused. */
export function useDemo(frame: RefObject<HTMLElement | null>, held: boolean) {
  const [state, dispatch] = useReducer(demoReducer, undefined, () => {
    const linked = sceneFromHash()
    if (linked) return stillState(linked)
    return prefersReducedMotion() ? stillState('digest') : startState
  })
  // Without IntersectionObserver (an old browser, a test), it counts as always on screen.
  const [inView, setInView] = useState(() => typeof IntersectionObserver === 'undefined')

  useEffect(() => {
    const node = frame.current
    if (!node || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: 0.35 })
    observer.observe(node)
    return () => observer.disconnect()
  }, [frame])

  const running = state.playing && inView && !held
  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => dispatch({ type: 'tick', ms: TICK }), TICK)
    return () => window.clearInterval(timer)
  }, [running])

  // Each scene has its own address (#demo-digest), so Back retraces the scenes a visitor chose.
  useEffect(() => {
    const onPop = () => {
      const scene = sceneFromHash()
      if (scene) dispatch({ type: 'go', scene })
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const go = useCallback((scene: Scene) => {
    if (window.location.hash !== `#demo-${scene}`) window.history.pushState(null, '', `#demo-${scene}`)
    dispatch({ type: 'go', scene })
  }, [])
  const toggle = useCallback(() => dispatch({ type: 'toggle' }), [])
  const pause = useCallback(() => dispatch({ type: 'pause' }), [])

  return { ...state, running, go, toggle, pause }
}
