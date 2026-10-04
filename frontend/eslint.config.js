import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // routeTree.gen.ts and api/schema.d.ts are generated; playwright-report is output.
  globalIgnores(['dist', 'src/routeTree.gen.ts', 'src/api/schema.d.ts', 'playwright-report', 'test-results']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    // shadcn components export their style variants next to the component, and TanStack
    // file routes export `Route` next to the component. Both are the documented patterns.
    files: ['src/components/ui/**', 'src/routes/**', 'tests/**', 'e2e/**'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
])
