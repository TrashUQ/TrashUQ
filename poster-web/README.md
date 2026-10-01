# TrashUQ poster web

Small Next.js landing page for the TrashUQ conference poster. It presents the project, headline results, repository, paper and team links.

## Run locally

```bash
npm ci
npm run dev
```

Open `http://localhost:3000`.

## Build and validate

```bash
npm run typecheck
npm run build
npm start -- -p 3001
```

Use port 3001 when the dashboard already occupies port 3000.

## Project and team links

Repository, paper, and author profile URLs are configured in `app/links.ts`. Each author currently has a direct LinkedIn URL; confirm these links before the presentation.
