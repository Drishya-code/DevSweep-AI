# DevSweep AI — Phase A Audit & Phase B Design Proposal

## Phase A: Comprehensive Audit

### 1. Architecture Overview

**Frontend Stack:**
- React 18 + TypeScript + Vite
- Tailwind CSS (dark mode via `class` strategy)
- React Router v6 for navigation
- React Context for global state (DevSweepContext)
- Vitest + React Testing Library for tests

**Backend Stack:**
- FastAPI + Python 3.14
- Nebius Token Factory + NVIDIA Nemotron models
- SQLite for persistence (planned)
- Pytest for tests

**Core Workflow:**
```
SCAN → AI ANALYZE → VALIDATE → PLAN → REVIEW → USER APPROVAL → EXECUTE → VERIFY → RESTORE
```

### 2. UX Problems Identified

#### A. No Adaptive Experience (Critical)
- **Problem:** Single presentation mode for all users
- **Impact:** Beginners overwhelmed by technical jargon; developers lack depth
- **Evidence:** Every page shows raw paths (`node_modules`, `.vite`), technical reasons ("Regenerable using package-lock.json"), risk codes (SAFE/CAUTION/DANGEROUS) without explanation

#### B. Information Hierarchy Issues
- **Dashboard:** Shows technical paths in "Storage Breakdown" table as primary view
- **ScanWorkspace:** Lists candidates with only path, risk badge, reason, size - no plain-language explanations
- **CleanupPlans:** Displays scanner→AI risk transitions (`SAFE → CAUTION`) as primary info, regeneration commands as technical badges
- **RestoreCenter:** Shows shell commands as primary interface

#### C. Inconsistent Design Patterns
- **Risk badges** implemented differently across 4+ pages (Dashboard, ScanWorkspace, CleanupPlans, RestoreCenter)
- **Format bytes** function duplicated in frontend (helpers.ts) and backend (3+ files)
- **Empty states** vary: some show illustrations, others plain text
- **Loading states** inconsistent: some use `Loader2` spinner, others disable buttons only
- **Error states** vary: inline alerts, toast-like banners, form-level errors

#### D. Missing Progressive Disclosure
- No "Show details" / "Explain this" affordances
- Technical details (full paths, regeneration commands, scanner/AI risk diff) always visible
- No contextual help system

#### E. Theme System Incomplete
- `darkMode: 'class'` configured but only dark colors defined
- No light theme color palette
- No theme toggle in UI (Settings has theme select but doesn't apply)

#### F. Accessibility Gaps
- Missing ARIA labels on icon-only buttons
- No focus-visible styles beyond default ring
- Table in Projects page lacks proper `<th scope="col">`
- Color-only risk indication (no text/icons for colorblind users)
- No skip links

#### G. Responsive Issues
- Dashboard stats grid: `lg:grid-cols-4` breaks on mobile
- ScanWorkspace candidate cards: horizontal layout overflows on small screens
- CleanupPlans table: horizontal scroll needed on mobile
- Sidebar: fixed `w-64`, no mobile drawer

#### H. Component Duplication
| Component | Locations |
|-----------|-----------|
| Risk badge rendering | Dashboard, ScanWorkspace, CleanupPlans, RestoreCenter, TopBar |
| `formatBytes` | helpers.ts, TopBar, 3+ backend files |
| `getRiskIcon` / `getRiskBadge` | ScanWorkspace, CleanupPlans, RestoreCenter |
| Empty state illustrations | Dashboard, Projects, ScanWorkspace, CleanupPlans, RestoreCenter, CleanupHistory |

### 3. Backend Safety Architecture (Must Preserve)

✅ **Validated & Working:**
- AI recommends → deterministic backend validates
- AI never directly deletes files
- User must approve cleanup
- DANGEROUS items never deleted
- CAUTION items require explicit approval
- Protected paths remain protected
- Backend independently validates candidates and plans
- Client-supplied paths/risks/actions never trusted
- Project-scoped, one-use, expiring AI analysis authorization
- Cleanup verification with snapshot associations
- No secrets/filesystem contents sent to AI provider

### 4. Current Page-by-Page Assessment

| Page | Status | Key Issues |
|------|--------|------------|
| **Dashboard** | Functional | Technical table as primary view; no simple summary |
| **Projects** | Functional | Table-only view; no card view for simple mode |
| **ScanWorkspace** | Functional | 3-step flow clear but technical; no explanations |
| **CleanupPlans** | Functional | Dense technical detail; approval UX good |
| **CleanupHistory** | Preview only | Not implemented |
| **RestoreCenter** | Preview only | Command-focused; no guided restore |
| **AIAgent** | Functional | Chat-only; no structured actions |
| **Settings** | Functional | Theme selector non-functional; demo mode works |

---

## Phase B: Design Proposal

### 1. Product Experience Direction

#### Core Philosophy: "Progressive Transparency"
- **Simple View:** Plain language first, technical details on demand
- **Technical View:** Full detail by default, nothing hidden
- **Shared Safety:** Backend rules identical in both views

#### Adaptive Behavior
- **Explicit toggle** in TopBar (prominent, not buried in Settings)
- **Persisted** in localStorage + synced to backend config
- **Per-project override** option
- **Never** changes backend validation

---

### 2. Simple View Design

#### Design Principles
| Principle | Implementation |
|-----------|----------------|
| **Plain language** | "Temporary build files" not "dist directory" |
| **Explain purpose** | "Created by Vite to speed up development" |
| **Explain regenerability** | "Can be recreated with `npm run build`" |
| **Explain consequences** | "Next build will take longer" |
| **Visual clarity** | Icons + color + text labels (not color-only) |
| **Guided steps** | Numbered workflow with clear CTAs |

#### Page-Level Simple View Specs

**Dashboard - Simple**
```
┌─────────────────────────────────────────────────────────┐
│  DevSweep AI                    [Simple ▼] [Technical]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📊 Your Workspace Health: ✅ Healthy                   │
│                                                         │
│  💾 Storage Used: 2.3 GB    ♻️ Recoverable: 1.8 GB     │
│                                                         │
│  What's taking up space?                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 📦 Dependencies (node_modules)     1.2 GB       │   │
│  │    Created by npm to store packages.            │   │
│  │    Can be recreated: Run `npm install`          │   │
│  │    [Show details ▼]                              │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 🏗️ Build Output (dist)              400 MB      │   │
│  │    Created when you build your project.         │   │
│  │    Can be recreated: Run `npm run build`        │   │
│  │    [Show details ▼]                              │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 🗂️ Cache Files (.vite, .cache)      200 MB      │   │
│  │    Temporary files to speed up development.     │   │
│  │    Can be recreated automatically.              │   │
│  │    [Show details ▼]                              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Scan Another Project]  [Clean Up 1.8 GB Now]       │
└─────────────────────────────────────────────────────────┘
```

**ScanWorkspace - Simple**
```
Step 1 of 3: Scan
┌─────────────────────────────────────────────────────────┐
│  Select a folder to analyze                             │
│  [/path/to/project                    ] [Scan]         │
│                                                         │
│  💡 Tip: DevSweep only looks for safe-to-remove files  │
│      like caches, build outputs, and dependencies.     │
│      Your source code is never touched.                 │
└─────────────────────────────────────────────────────────┘

Step 2 of 3: Review (after scan)
┌─────────────────────────────────────────────────────────┐
│  Found 3 items that can be cleaned (1.8 GB total)      │
│                                                         │
│  ☑️ Dependencies (node_modules) - 1.2 GB              │
│     Safe to remove • Recreated by `npm install`        │
│     [Why? ▼]                                           │
│                                                         │
│  ☑️ Build Output (dist) - 400 MB                      │
│     Safe to remove • Recreated by `npm run build`      │
│     [Why? ▼]                                           │
│                                                         │
│  ☑️ Cache Files (.vite, .cache) - 200 MB              │
│     Safe to remove • Recreated automatically           │
│     [Why? ▼]                                           │
│                                                         │
│  [← Back]                                    [Next →]  │
└─────────────────────────────────────────────────────────┘

Step 3 of 3: Confirm
┌─────────────────────────────────────────────────────────┐
│  Ready to clean up 1.8 GB?                             │
│                                                         │
│  ✅ Your source code, Git history, and settings        │
│     are PROTECTED and will not be touched.             │
│                                                         │
│  ⚠️ Next build will take longer (dependencies reinstall)│
│                                                         │
│  [Cancel]                         [Clean Up Now]       │
└─────────────────────────────────────────────────────────┘
```

**CleanupPlans - Simple**
```
┌─────────────────────────────────────────────────────────┐
│  Cleanup Plan for "my-react-app"                        │
│                                                         │
│  📋 3 items selected • 1.8 GB will be freed            │
│                                                         │
│  ☑️ Dependencies (node_modules) - 1.2 GB              │
│     Safe • Reinstall with: npm install                 │
│                                                         │
│  ☑️ Build Output (dist) - 400 MB                      │
│     Safe • Rebuild with: npm run build                 │
│                                                         │
│  ☑️ Cache Files (.vite, .cache) - 200 MB              │
│     Safe • Recreated automatically                     │
│                                                         │
│  ⚠️ What happens after cleanup?                        │
│  • Next `npm install` will re-download packages        │
│  • Next `npm run build` will regenerate dist/          │
│  • Your code, Git, and .env files are SAFE             │
│                                                         │
│  ☐ I understand this will delete the selected items    │
│                                                         │
│  [Cancel]                         [Approve & Clean]    │
└─────────────────────────────────────────────────────────┘
```

---

### 3. Technical View Design

#### Design Principles
| Principle | Implementation |
|-----------|----------------|
| **Full paths** | Relative paths from project root |
| **Scanner + AI risks** | Both shown with upgrade indicators |
| **Regeneration commands** | Exact commands, copyable |
| **Risk reasoning** | Scanner reason + AI reason separated |
| **Verification steps** | Explicit checklist |
| **Raw data access** | JSON export, full API responses |

#### Page-Level Technical View Specs

**Dashboard - Technical**
```
┌─────────────────────────────────────────────────────────┐
│  DevSweep AI                    [Simple] [Technical ▼]  │
├─────────────────────────────────────────────────────────┤
│  Project: /home/user/my-react-app (React + TypeScript) │
│  Git: Clean  •  Package Manager: npm  •  Framework: Vite│
│                                                         │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │  Storage │Recoverable│ Scans   │Total Opp │         │
│  │  2.3 GB  │  1.8 GB   │   12    │  14.2 GB │         │
│  └──────────┴──────────┴──────────┴──────────┘         │
│                                                         │
│  Cleanup Candidates (Scanner Risk / AI Risk)           │
│  ┌──────────────────────────────────────────────────┐  │
│  │ node_modules        │ SAFE / SAFE    │ 1.2 GB    │  │
│  │   Scanner: Regenerable from package-lock.json    │  │
│  │   AI: Confirmed regenerable                       │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ dist                │ SAFE / SAFE    │ 400 MB    │  │
│  │   Scanner: Generated build output                 │  │
│  │   AI: Confirmed regenerable                       │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ .vite               │ SAFE / SAFE    │ 200 MB    │  │
│  │   Scanner: Vite cache directory                   │  │
│  │   AI: Confirmed regenerable                       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  Protected: .git, src/, package.json, .env, ... (47)   │
│  [Scan Again]  [View All Candidates]  [Create Plan]    │
└─────────────────────────────────────────────────────────┘
```

---

### 4. Shared Component System

#### Design Tokens (New: `src/design-tokens.ts`)
```typescript
// Spacing scale
export const spacing = {
  xs: '4px', sm: '8px', md: '16px', lg: '24px', xl: '32px', xxl: '48px'
}

// Typography scale
export const typography = {
  display: 'text-4xl font-bold tracking-tight',
  h1: 'text-3xl font-bold', h2: 'text-2xl font-semibold',
  h3: 'text-xl font-semibold', h4: 'text-lg font-medium',
  body: 'text-base', bodySm: 'text-sm', caption: 'text-xs',
  mono: 'font-mono text-sm', monoXs: 'font-mono text-xs'
}

// Semantic colors (light + dark)
export const colors = {
  light: {
    bg: '#ffffff', bgSecondary: '#f6f8fa', bgTertiary: '#eaeef2',
    border: '#d0d7de', borderHover: '#8b949e',
    text: '#1f2328', textSecondary: '#656d76', textMuted: '#8b949e',
    accent: '#0969da', accentHover: '#0860ca',
    success: '#1a7f37', warning: '#9a6700', danger: '#cf222e', dangerHover: '#a40e26',
  },
  dark: {
    bg: '#0d1117', bgSecondary: '#161b22', bgTertiary: '#21262d',
    border: '#30363d', borderHover: '#484f58',
    text: '#f0f6fc', textSecondary: '#8b949e', textMuted: '#6e7681',
    accent: '#58a6ff', accentHover: '#79b8ff',
    success: '#3fb950', warning: '#d29922', danger: '#f85149', dangerHover: '#ff7b72',
  }
}

// Risk colors (consistent across views)
export const riskColors = {
  SAFE: { bg: 'success/10', text: 'success', border: 'success/20', icon: '✓', label: 'Safe' },
  CAUTION: { bg: 'warning/10', text: 'warning', border: 'warning/20', icon: '⚠', label: 'Caution' },
  DANGEROUS: { bg: 'danger/10', text: 'danger', border: 'danger/20', icon: '✕', label: 'Dangerous' },
}
```

#### Shared Components (New: `src/components/ui/`)

| Component | Purpose | Variants |
|-----------|---------|----------|
| `Button` | Primary actions | primary, secondary, ghost, danger, loading |
| `Card` | Content containers | default, outlined, elevated |
| `Badge` | Status labels | risk (SAFE/CAUTION/DANGEROUS), status, info |
| `RiskBadge` | Risk with icon+text | simple (icon+label), technical (scanner/AI/effective) |
| `ExpandableSection` | Progressive disclosure | controlled/uncontrolled, animate |
| `EmptyState` | No-data illustrations | scan, project, history, cleanup |
| `LoadingState` | Skeleton/spinner | inline, overlay, button |
| `ErrorAlert` | Error display | inline, banner, toast |
| `DataTable` | Tabular data | sortable, selectable, responsive |
| `Stepper` | Multi-step flows | horizontal, vertical, numbered |
| `ToggleSwitch` | Binary settings | with labels, controlled |

#### Adaptive Wrapper Components
```tsx
// Usage in pages
<AdaptiveView>
  <SimpleView>
    <SimpleCandidateList candidates={candidates} />
  </SimpleView>
  <TechnicalView>
    <TechnicalCandidateTable candidates={candidates} />
  </TechnicalView>
</AdaptiveView>
```

---

### 5. Navigation Structure

#### Sidebar (Persistent)
```
DevSweep AI
├── Dashboard          ← Overview + quick actions
├── Projects           ← Project switcher + history
├── Scan Workspace     ← Scan → Analyze → Plan
├── Cleanup Plans      ← Review → Approve → Execute
├── Cleanup History    ← Audit trail (future)
├── Restore Center     ← Rebuild guidance (future)
├── AI Agent           ← Chat + quick actions
└── Settings           ← Config + view mode toggle
```

#### TopBar (Persistent)
```
[DevSweep Logo]  [Project: my-app ▼]     [Storage: 2.3GB] [Recoverable: 1.8GB] [Health: ✅]  [Simple ▼] [Technical]  [Theme] [Demo]
```

---

### 6. Page Redesigns

#### 6.1 Dashboard
**Simple View:**
- Health status card (large, visual)
- Two big numbers: Storage Used / Recoverable
- Top 3 cleanup opportunities as expandable cards
- Primary CTA: "Clean Up Now"

**Technical View:**
- Current project metadata badges
- 4-stat grid (Storage, Recoverable, Scans, Total)
- Full candidate table with scanner/AI risk columns
- Protected paths list (collapsible)

#### 6.2 Projects
**Simple View:**
- Card grid with project name, last scan, recoverable space
- "Scan New Project" prominent
- One-click "Select & Scan"

**Technical View:**
- Current table (enhanced with sort/filter)
- Column visibility toggle
- Bulk actions

#### 6.3 Scan Workspace (3-Step Wizard)

**Step 1: Scan** — Same in both views
- Path input + Scan button
- Demo project option
- Recent paths dropdown

**Step 2: Review** — Adaptive
- Simple: Cards with plain explanations + "Why?" expanders
- Technical: Table with all risk columns, regeneration commands

**Step 3: Confirm** — Adaptive
- Simple: Plain-language summary + checkbox + big button
- Technical: Full plan table + approval checkbox + verification steps

#### 6.4 Cleanup Plans
**Simple View:**
- Plan summary card (items count, total space)
- Item cards: name, simple risk, plain explanation, regeneration hint
- "What happens after?" info panel
- Approval checkbox + Execute button

**Technical View:**
- Current dense table (improved with sticky headers)
- Scanner/AI/Effective risk columns
- Regeneration command column (copyable)
- Warnings + Verification steps panels
- Approval + Execute

#### 6.5 Restore Center (Future-Ready)
**Simple View:**
- Guided options: "Reinstall Dependencies", "Rebuild Project", "Full Setup"
- Each with: plain description, estimated time, one-click copy commands
- Prerequisites checklist

**Technical View:**
- Current command list + raw commands
- Manifest export/import
- Custom command sequences

---

### 7. Theme System (Light + Dark)

#### Light Theme Colors (New)
```css
:root[data-theme="light"] {
  --devsweep-bg: #ffffff;
  --devsweep-bgSecondary: #f6f8fa;
  --devsweep-bgTertiary: #eaeef2;
  --devsweep-border: #d0d7de;
  --devsweep-borderHover: #8b949e;
  --devsweep-text: #1f2328;
  --devsweep-textSecondary: #656d76;
  --devsweep-textMuted: #8b949e;
  --devsweep-accent: #0969da;
  --devsweep-accentHover: #0860ca;
  --devsweep-success: #1a7f37;
  --devsweep-warning: #9a6700;
  --devsweep-danger: #cf222e;
  --devsweep-dangerHover: #a40e26;
}
```

#### Theme Toggle Location
- TopBar: Sun/Moon icon button (always visible)
- Settings: Radio group (Light / Dark / System)
- Persisted in localStorage + CSS `data-theme` on `<html>`

---

### 8. Implementation Order

#### Phase C1: Foundation (Week 1)
1. **Design tokens** (`src/design-tokens.ts`)
2. **Theme system** (light colors + toggle + persistence)
3. **Shared UI components** (Button, Card, Badge, RiskBadge, ExpandableSection, EmptyState, LoadingState, ErrorAlert, DataTable, Stepper)
4. **AdaptiveView wrapper** + view mode context + TopBar toggle

#### Phase C2: Core Pages - Adaptive (Week 2)
5. **Dashboard** — both views
6. **Projects** — both views
7. **ScanWorkspace** — 3-step wizard with adaptive Step 2/3

#### Phase C3: Plans & Execution (Week 3)
8. **CleanupPlans** — both views
9. **Execute/Verify flow** — adaptive confirmation + results
10. **RestoreCenter** — simple guided + technical

#### Phase C4: Polish (Week 4)
11. **AIAgent** — structured actions + adaptive responses
12. **Settings** — functional theme toggle, view mode default
13. **CleanupHistory** — implement with adaptive views
14. **Responsive fixes** — mobile drawer, table stacking, card layouts
15. **Accessibility audit** — ARIA, focus, contrast, keyboard

---

### 9. Files to Modify (Estimated)

#### New Files (~15)
```
src/design-tokens.ts
src/context/ViewModeContext.tsx
src/components/ui/Button.tsx
src/components/ui/Card.tsx
src/components/ui/Badge.tsx
src/components/ui/RiskBadge.tsx
src/components/ui/ExpandableSection.tsx
src/components/ui/EmptyState.tsx
src/components/ui/LoadingState.tsx
src/components/ui/ErrorAlert.tsx
src/components/ui/DataTable.tsx
src/components/ui/Stepper.tsx
src/components/ui/ToggleSwitch.tsx
src/components/AdaptiveView.tsx
src/hooks/useViewMode.ts
```

#### Modified Files (~12)
```
src/index.css                    ← Light theme colors
src/tailwind.config.js           ← Extend with design tokens
src/context/DevSweepContext.tsx  ← Add viewMode state
src/components/TopBar.tsx        ← View mode toggle + theme toggle
src/components/Sidebar.tsx       ← Mobile drawer support
src/pages/Dashboard.tsx          ← Full adaptive rewrite
src/pages/Projects.tsx           ← Card view + adaptive table
src/pages/ScanWorkspace.tsx      ← 3-step wizard + adaptive
src/pages/CleanupPlans.tsx       ← Full adaptive rewrite
src/pages/RestoreCenter.tsx      ← Guided restore + adaptive
src/pages/Settings.tsx           ← Functional theme/view toggles
src/utils/helpers.ts             ← Consolidate formatBytes, risk utils
```

#### Backend Changes (Minimal)
- Add `view_mode` to `/api/config` response
- Store user preference in settings DB (future)

---

### 10. Why These Decisions Improve Experience

| Decision | Rationale |
|----------|-----------|
| **Explicit view toggle in TopBar** | Discoverable, one-click switch, persists per-user |
| **Simple View = progressive disclosure** | Reduces cognitive load; details available on demand |
| **Technical View = full density** | Developers see everything without clicking |
| **Shared safety backend** | Zero risk of view mode affecting security |
| **Design tokens first** | Consistency, maintainability, theme support |
| **Stepper for Scan→Analyze→Plan** | Clear workflow, prevents skipping AI analysis |
| **RiskBadge with icon+text** | Accessible (not color-only), consistent |
| **ExpandableSection** | Reusable progressive disclosure pattern |
| **Light theme** | Accessibility, user preference, professional polish |
| **Mobile drawer** | Usable on laptops/tablets |

---

### 11. Known Limitations & Risks

| Risk | Mitigation |
|------|------------|
| Scope creep in Phase C | Strict page-by-page implementation order |
| Duplicate logic during transition | Shared components first; refactor pages to use them |
| Theme flash on load | Initialize theme from localStorage in `index.html` script |
| Test breakage | Update tests incrementally per page; maintain coverage |
| Mobile performance | Lazy-load heavy components; virtualize long lists |

---

### 12. Approval Request

**Please review and approve this design proposal before Phase C implementation begins.**

Key decisions needing confirmation:
1. ✅ Two-view adaptive approach (Simple/Technical)
2. ✅ TopBar toggle for view mode (not just Settings)
3. ✅ Light theme implementation alongside dark
4. ✅ 3-step wizard for ScanWorkspace
5. ✅ Progressive disclosure via ExpandableSection
6. ✅ Shared component library first
7. ❓ Any specific competitor/product references for visual direction?
8. ❓ Priority: CleanupPlans vs Dashboard vs ScanWorkspace for first adaptive page?
9. ❓ RestoreCenter: implement fully now or keep as preview?

---

**Next Step:** Upon approval, begin Phase C1 with design tokens and shared UI components.