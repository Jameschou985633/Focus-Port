# FocusHub Homepage Acceptance Checklist

## 1) Visual
- [ ] Core chain is identifiable in 3 seconds: Goal -> Action -> Duration -> Start.
- [ ] Start Focus is the only primary CTA.
- [ ] Next Action card is visually stronger than all secondary blocks.
- [ ] Secondary area does not compete for primary focus.

## 2) Interaction
- [ ] 15/25/45 can be toggled.
- [ ] Start click immediately shows Booting...
- [ ] Repeated Start clicks are locked during booting.
- [ ] Duration toggle is locked during booting.
- [ ] Master task click opens phase drawer.
- [ ] Drawer supports backdrop close and Esc close.

## 3) State
- [ ] Idle state is complete and readable.
- [ ] Loading state uses skeleton or smooth transition with no layout jump.
- [ ] In Focus state is de-noised and keeps only critical actions.
- [ ] Empty state shows Call AI Planner and disables Start.

## 4) Responsive
- [ ] No horizontal overflow at 1440.
- [ ] No horizontal overflow at 1366.
- [ ] Mobile 390 shows core chain first in viewport.

## 5) Regression
- [ ] Master task selection works.
- [ ] Phase drawer management works.
- [ ] Back to map and enter city actions work.
- [ ] No route, action signature, or API contract changes.
- [ ] npm run build passes.
