# Document Copilot landing page

Static, single-page site for the project (Vite + React + TypeScript). All interactions run client-side on recorded answers from the real app; nothing calls the backend.

```bash
pnpm install
pnpm dev       # http://localhost:5173
pnpm build     # output in dist/
```

## Deploy

`.github/workflows/deploy-landing.yml` builds and publishes `dist/` to GitHub Pages on every push to `main` that touches `landing-page/`. One-time setup: repo **Settings → Pages → Source: GitHub Actions**. The site is served at `https://furkanturan8.github.io/document-copilot/`; `base: './'` in `vite.config.ts` keeps asset paths relative to that subpath.

## Media

The Sessions carousel (section 07) does not play video: `src/AppReplay.tsx` rebuilds the app's chat screen and replays each recorded session from `src/replays.ts` (same questions, answers, status lines and citations as `docs/media/`). The videos only play in the "Watch the demo" modal.

`public/media/` holds web-encoded copies of the three `docs/media/*.mp4` recordings (1440 px wide, no audio) with the test account's email masked by copying the empty sidebar strip above it over the account row:

```bash
ffmpeg -i docs/media/NAME.mp4 -an -filter_complex "[0]split[a][b];[b]crop=338:78:0:780[p];[a][p]overlay=0:858,scale=1440:-2" \
  -c:v libx264 -crf 26 -preset slow -pix_fmt yuv420p -movflags +faststart landing-page/public/media/NAME.mp4
ffmpeg -ss 1 -i landing-page/public/media/NAME.mp4 -frames:v 1 -q:v 3 landing-page/public/media/NAME.jpg   # poster
```

## Content

All copy (EN/TR), recorded answers and citations live in `src/content.ts`. Answers, page numbers and quotes match the recordings and the filing text in `data/markdown/`; keep them that way when editing.
