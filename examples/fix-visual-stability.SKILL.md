---
name: assess and fix nextjs performance
description: Diagnose and fix Next.js visual instability issues including CLS, layout shifts, and hydration flicker
---
## Steps
1. Run npx ts-node measure.ts http://localhost:3000 to measure page performance and identify sequential API bottlenecks
2. Run npx ts-node measure-cls.ts http://localhost:3000 --scroll to measure Cumulative Layout Shift
3. Run npx ts-node detect-flicker.ts http://localhost:3000 to detect theme flicker from localStorage/cookie reads before hydration
4. Analyze metrics: totalMs >1000ms is red flag, JSHeapUsedSize growth indicates memory leak, LayoutCount shows reflow issues
5. Reference rules directory for optimization patterns (async-parallel.md, rendering-hydration-no-flicker.md)
6. Fix CLS: add explicit width/height on all images, use loading='lazy' below-fold, priority='high' above-fold
7. Fix theme flicker: insert inline script in document head to read localStorage before React hydration
8. Fix sequential APIs: refactor to Promise.all() for parallel execution
9. Avoid layout reads (getBoundingClientRect, offsetHeight) in render path
## Constraints
- Don't break existing functionality or change class names/ids/data-testid (tests rely on them)
- No images without explicit dimensions
- No layout reads in render path
- Playwright must be pre-installed before running measurement scripts
## Dependencies
- Playwright (pre-installed)
- ts-node
- Rules directory (rules/async-parallel.md, rules/rendering-hydration-no-flicker.md)
## Examples
- Example 1: {"input": "Sequential /api/products (512ms) → /api/featured (301ms) → /api/categories (201ms)", "output": "Total 1014ms - BAD. Use Promise.all() for parallel execution"}
- Example 2: {"input": "<img src='...' /> without dimensions causing CLS", "output": "Add explicit width and height: <img src='...' width={300} height={200} loading='lazy' />"}
