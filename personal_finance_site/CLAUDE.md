# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Static educational website about personal finance in Switzerland. Pure vanilla HTML/CSS/JavaScript — no build system, no package manager, no frameworks, no external dependencies.

## Development

To serve locally, use any static file server from the project root:

```bash
python3 -m http.server 8000
```

There are no build steps, tests, or linting configured.

## Architecture

Three files make up the entire site:

- **index.html** — Single-page site with 8 topic sections (Budgeting, Emergency Fund, Debt, Insurance, 3-Pillar System, Investing, Tax Optimization, Estate Planning). All content is Swiss-specific.
- **style.css** — Dark theme using CSS custom properties for theming. Responsive breakpoints at 768px and 480px. Uses glassmorphism effects (backdrop-filter).
- **script.js** — Four features: mobile nav toggle, active nav highlighting on scroll, section reveal animations via IntersectionObserver, and navbar background opacity on scroll. All scroll listeners use `{ passive: true }`.

## Key Design Decisions

- CSS variables define the entire color palette and spacing system — modify variables rather than individual values when changing the theme.
- The 3-pillar retirement section uses a special 3-column grid layout that collapses to 1 column on mobile.
- This project is part of a larger Finance monorepo (stock analyzer, robo advisor) hosted at GitHub under `Themuray/Finance`.
