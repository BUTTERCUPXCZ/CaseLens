import { z } from 'zod'

// Zod would otherwise compile its validators with new Function(), which our strict
// Content-Security-Policy (no unsafe-eval) forbids. The forms are tiny; interpreting is fast enough.
// This lives in its own module, imported first by main.tsx, because route files create their
// schemas at import time and the setting must already be in place by then.
z.config({ jitless: true })
