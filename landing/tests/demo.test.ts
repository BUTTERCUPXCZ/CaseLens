import { describe, expect, it } from 'vitest'

import { stageAt } from '@/demo/stages'
import { DURATION, demoReducer, startState, stillState } from '@/demo/useDemo'

describe('the replica', () => {
  it('plays the scenes in the app’s order and stops at the end', () => {
    let state = startState
    const seen = [state.scene]
    for (let i = 0; i < 400 && state.playing; i++) {
      state = demoReducer(state, { type: 'tick', ms: 100 })
      if (seen.at(-1) !== state.scene) seen.push(state.scene)
    }
    expect(seen).toEqual(['find', 'write', 'digest', 'download'])
    expect(state).toMatchObject({ scene: 'download', playing: false, finished: true, t: DURATION.download })
  })

  it('does not move while paused', () => {
    const paused = demoReducer(startState, { type: 'toggle' })
    expect(demoReducer(paused, { type: 'tick', ms: 5000 })).toBe(paused)
  })

  it('opens a chosen step from its start while playing, and finished while paused', () => {
    expect(demoReducer(startState, { type: 'go', scene: 'digest' })).toMatchObject({ scene: 'digest', t: 0, playing: true })
    const paused = demoReducer(startState, { type: 'pause' })
    expect(demoReducer(paused, { type: 'go', scene: 'write' })).toEqual(stillState('write'))
  })

  it('plays again from the first step after it finished', () => {
    const finished = { ...stillState('download'), finished: true }
    expect(demoReducer(finished, { type: 'toggle' })).toEqual(startState)
  })

  it('moves the progress bar through the app’s steps without going back', () => {
    const stages = [0, 700, 3400, 5000].map((t) => stageAt(t).stage)
    expect(stages).toEqual(['queued', 'writing', 'checking', 'repairing'])
    let last = -1
    for (let t = 0; t <= DURATION.write; t += 100) {
      const { percent } = stageAt(t)
      expect(percent).toBeGreaterThanOrEqual(last)
      last = percent
    }
    expect(stageAt(DURATION.write).percent).toBe(100)
  })
})
