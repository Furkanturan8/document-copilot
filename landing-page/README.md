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

`public/media/` holds web-encoded copies of `docs/media/` (1440 px wide, no audio) with the test account's email masked by copying the empty sidebar strip above it over the account row:

```bash
# videos (1920x936 source)
ffmpeg -i docs/media/NAME.mp4 -an -filter_complex "[0]split[a][b];[b]crop=338:78:0:780[p];[a][p]overlay=0:858,scale=1440:-2" \
  -c:v libx264 -crf 26 -preset slow -pix_fmt yuv420p -movflags +faststart landing-page/public/media/NAME.mp4
# stills (2880x1404 source)
ffmpeg -i docs/media/NAME.png -filter_complex "[0]split[a][b];[b]crop=508:121:0:1160[p];[a][p]overlay=0:1283,scale=1440:-2" \
  -q:v 3 landing-page/public/media/NAME.jpg
```

Video posters are the frame at 1 s (`ffmpeg -ss 1 -i NAME.mp4 -frames:v 1 -q:v 3 NAME.jpg`).

## Content

All copy (EN/TR), recorded answers and citations live in `src/content.ts`. Answers, page numbers and quotes match the recordings and the filing text in `data/markdown/`; keep them that way when editing.
