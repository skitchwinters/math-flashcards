# Jessup Math Flashcards

A bespoke, responsive web application for studying mathematical definitions across Jessup University upper-division courses:
- **MATH 301**: Discrete Mathematics (*Book of Proof* by Richard Hammack) — 74 definitions across 10 chapters.
- **MATH 410**: Abstract Algebra (*Contemporary Abstract Algebra* by Joseph Gallian) — 97 definitions across 10 chapters.
- **MATH 461**: Real Analysis (*Elementary Classical Analysis* by Jerrold E. Marsden & Michael J. Hoffman) — 120 definitions across 5 chapters.

## Features
- **Desktop & Mobile Optimized**: Responsive layout with touch targets and keyboard navigation (`Space`/`Enter` to flip, `ArrowRight`/`ArrowLeft` to navigate).
- **Proper Mathematical Notation**: Powered by KaTeX with custom macros (`\C`, `\R`, `\N`, `\Z`, `\Q`, `\id`, `\mod`, `\cyc`, `\ip`, `\intr`, `\dom`).
- **3D Card Flip Animation**: Smooth CSS 3D transforms reveal the definition upon tapping or clicking the card or the "Flip" button.
- **Flexible Chapter Selection**: Study specific chapters or the entire course with one-click toggles and live card counts.
- **Randomized Deck**: Cards are shuffled with Fisher-Yates randomization.
- **Completion Flows**: Instant options to "Start Over", "Choose Different Chapters", or "Back to Main Menu".
- **PWA & Offline Capable**: Bundled service worker (`sw.js`) caches definitions and styles for offline study on mobile devices.

## Project Structure
```
math-flashcards/
├── index.html            # Main semantic application view
├── style.css             # Responsive styling with 3D card flips & dark slate theme
├── app.js                # State machine, event listeners, KaTeX math rendering
├── definitions.js        # Bundled definition data (291 terms across 3 courses)
├── definitions.json      # Structured JSON definition dataset
├── sync_definitions.py   # Extraction script pulling latest .tex files from GitHub
├── deploy.py             # One-command production deployment to Vercel
├── manifest.json         # Progressive Web App manifest
└── sw.js                 # Offline service worker cache
```

## How to Synchronize Definitions
To fetch and re-parse definitions from the GitHub repositories (`MATH-301-Extras`, `MATH-410-Extras`, `MATH-461-Extras`):
```bash
python sync_definitions.py
```

## How to Deploy to Vercel
Run the deployment script:
```bash
python deploy.py
```
Or push to a GitHub repository connected to Vercel.
