# FocusHub Homepage Figma Playbook (Homepage Only)

## Goal
- Build one clear action chain: `Current Goal -> Next Action -> Duration -> Start Focus`
- Keep business entry points: master task, phase drawer, pomodoro, map and city entry
- Do not expand to other pages

## Step 0 (30 min): File and foundation
1. Create 5 Figma pages:
   - `00_Foundation`
   - `10_Wireframe`
   - `20_HighFi`
   - `30_Prototype`
   - `40_Handoff`
2. Create variables in `00_Foundation`:
   - Colors: dark navy base, blue/cyan highlight, weak border, weak text
   - Spacing: 4/8/12/16/24/32/40/48/64
   - Radius: 10/14/18/22/999
   - Shadow: `soft / panel / glow`
   - Type scale: `xs/sm/base/lg/xl/2xl/3xl`
3. Create fixed breakpoints:
   - `Desktop-Main`: 1440
   - `Desktop-Regression`: 1366
   - `Mobile`: 390

## Step 1 (45 min): Wireframe only
1. In `10_Wireframe`, define only structure:
   - Top bar: logo + back to map + enter city + message/avatar slot
   - Core area: goal, action card, 15/25/45, start focus
   - Secondary area: master task list card (no long phase list)
2. Hard rule:
   - Only one primary CTA on homepage: `Start Focus`

## Step 2 (60-90 min): High fidelity
1. In `20_HighFi`, set visual priority:
   - `Next Action Card` is the strongest visual
   - `Start Focus` is second strongest
   - Pomodoro and To-do are de-emphasized
2. To-do pattern:
   - Homepage shows only master task list
   - Phase details live in drawer only
3. Required state frames:
   - `Idle`
   - `Loading` (button text `Booting...`)
   - `In Focus`
   - `Empty` (show "Call AI Planner")

## Step 3 (30-45 min): Prototype loop
1. Build minimal loop:
   - switch duration -> click start -> enter in-focus
   - in-focus controls: pause, complete, abort
   - click master task -> open phase drawer
2. Motion rule:
   - use `ease-out`
   - use only `fade + translateY + micro scale`

## Step 4 (20 min): Handoff package
1. Put 6 screenshots in `40_Handoff`:
   - Desktop: `Idle / Loading / InFocus / Empty`
   - Mobile: `Idle / InFocus`
2. Use these component names:
   - `FocusHomeShell`
   - `TopSystemBar`
   - `ActionCorePanel`
   - `PomodoroCard`
   - `MasterTaskCard`
   - `MasterTaskDrawer`
3. Add 3 constraints per component:
   - Input data
   - Interactions
   - Do-not rules
