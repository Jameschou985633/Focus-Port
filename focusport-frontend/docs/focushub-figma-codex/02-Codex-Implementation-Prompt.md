# FocusHub Homepage Refactor: Copy-Paste Prompt for Codex

```text
You are a senior frontend engineer. Refactor FocusHub homepage in a Vue 3 + Tailwind project.
Scope is homepage only.

[Goal]
Make homepage an action hub with this fixed chain:
Current Goal -> Next Action -> Duration(15/25/45) -> Start Focus

[Hard constraints]
1) Do not change routes, backend APIs, or existing store action signatures.
2) Keep existing business entry points: master task, phase drawer, pomodoro, back to map, enter city.
3) Homepage must have one and only one primary CTA: Start Focus.
4) Change only homepage UI and interaction states.

[Component names]
- FocusHomeShell
- TopSystemBar
- ActionCorePanel
- PomodoroCard
- MasterTaskCard
- MasterTaskDrawer

[Layout]
1) Top bar: logo + back to map + enter city + message/avatar slot.
2) Core area (highest visual priority):
   - Current Goal
   - Next Action Card (strongest visual)
   - Duration 15/25/45
   - Start Focus (the only primary CTA)
3) Secondary area:
   - Master task list card (title, progress, next phase only)
   - Phase details shown in drawer only

[Required states]
- Idle
- Loading (show Booting... immediately after Start click)
- In Focus
- Empty (show "Call AI Planner")

[Interaction rules]
1) 15/25/45 must be selectable.
2) On Start click:
   - set button text to Booting...
   - prevent repeated clicks
   - lock duration toggles
3) Clicking a master task opens phase drawer.
4) Drawer supports Esc close and backdrop close.

[Visual rules]
- Dark navy or slate base with cyan or blue glow accents.
- Next Action card is brightest, Start button is second brightest.
- To-do and pomodoro cards are de-emphasized.
- Motion uses ease-out and only fade, translateY, micro-scale.

[Commit order]
- Commit A: layout skeleton only
- Commit B: visual styling
- Commit C: state and interaction locks
- Run npm run build after each commit

[Acceptance]
1) User can recognize core chain in 3 seconds.
2) No horizontal overflow at 1440, 1366, 390.
3) In Focus state is visually de-noised.
4) No regression in existing business chain.
```
