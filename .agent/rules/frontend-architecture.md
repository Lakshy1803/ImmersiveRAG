# Frontend React & Next.js Standards
- **Component Architecture**: Use strictly functional React components (`export function ComponentName(props: ComponentProps)`).
- **TypeScript**: Define explicit `interface`s for Props and States.
- **Next.js Rules**: Always prepend `'use client';` on interactive components using hooks. Keep server-side state minimal.
- **Styling**: Use Tailwind CSS v4 utility classes linked to design tokens (`bg-surface-container`, `text-primary`). Avoid custom CSS.
- **Typography & Icons**: Use Google Material Symbols (`<span className="material-symbols-outlined">...</span>`).
- **Networking**: Use native `fetch()` alongside `AbortController`.
- **Markdown Parsing**: Use `react-markdown` and `remark-gfm` to render LLM responses. Apply Tailwind prose styling.
