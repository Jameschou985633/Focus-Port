# FocusHub Component Constraint Template

## FocusHomeShell
- Input: page-level states (Idle, Loading, InFocus, Empty), selected master task, timer status.
- Interaction: compose child events (start, duration toggle, open drawer, enter city).
- Do not: add new business APIs or change existing action signatures.

## TopSystemBar
- Input: username and status label.
- Interaction: emit go-home, back-map, enter-city.
- Do not: introduce a second primary CTA.

## ActionCorePanel
- Input: currentGoal, nextAction, durationOptions, selectedDuration, loading and empty states.
- Interaction: emit select-duration, start-focus, call-ai.
- Do not: render another main CTA or overpower secondary content.

## PomodoroCard
- Input: formattedRemaining, isRunning, focusMinutes, durationLocked.
- Interaction: pause, resume, abort, quick-complete (existing action chain only).
- Do not: bypass existing start/deploy/link flow.

## MasterTaskCard
- Input: master task list (title, progress, next phase, status).
- Interaction: select task, open drawer, optional create task.
- Do not: expand long phase list on homepage.

## MasterTaskDrawer
- Input: current master task and phases.
- Interaction: add, edit, reorder, delete, start phase; Esc and backdrop close.
- Do not: interrupt core timer display.
