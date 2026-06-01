# Usability Testing Plan — Powercoders Learning Journey Hub

**Version:** 1.1 · May 2026  
**Required by:** Project brief — basic usability testing with **at least 5 participants**

**Environment:** use the shared **tester** URL (Render `deploy` branch) or local Docker with seed users — see [DEPLOY.md](DEPLOY.md) and [SETUP.md](SETUP.md).

---

## Goals

1. Validate core flows (journal, goals, weekly reflection, group) without hand-holding.
2. Find confusing UI, missing feedback, or unclear labels before a full cohort rollout.
3. Record findings with severity so the team can prioritise fixes.

---

## Participants

| # | Role | Recruitment |
|---|------|-------------|
| 2 | Students (bootcamp) | Volunteer from current cohort |
| 2 | Students (connecting programme) | Volunteer from current cohort |
| 1 | Teacher | Teaching team |

**Minimum:** 5 (≥1 teacher, ≥4 students).  
**Compensation:** Acknowledge contribution; no payment required.

---

## Session format

- **Duration:** 30–40 minutes
- **Format:** Moderated; remote or in-person
- **Device:** Participant laptop (mobile optional for spot-checks)
- **Recording:** Screen + audio with consent; otherwise written notes
- **Facilitator:** one leads; second takes notes if possible

---

## Test script

### Introduction (5 min)

> "We're testing the platform — not you. Think aloud: what you expect, what surprises you. Confusion helps us improve."

Provide test credentials privately (not in this repo).

### Tasks — students

| # | Task | Success criteria |
|---|------|------------------|
| T1 | Log in with provided credentials | Reaches dashboard without help |
| T2 | New journal entry (something learned this week); set mood; share with teacher | Entry saved and visible as shared |
| T3 | Create goal e.g. "Learn to write a REST API"; Hard Skill; **two milestones**; target date | Goal saved with 2 milestones |
| T4 | Mark one milestone complete | Progress updates |
| T5 | Submit **weekly reflection** (Reflections app) | Reflection saved |
| T6 | Open **Group** feed; read a teacher announcement | Finds post in group space |
| T7 | Profile → download personal data (**Markdown export**) | File downloads |
| T8 | (Optional) Post a file in group chat with **Resource** label; open **Resources** app | Resource appears on group tile |

### Tasks — teachers

| # | Task | Success criteria |
|---|------|------------------|
| T1 | Log in (2FA for staff) | Dashboard without help |
| T2 | See students missing weekly reflection | Teacher dashboard indicator / list |
| T3 | Open student progress → student detail → latest shared journal | Entry visible |
| T4 | Leave feedback on a journal entry | Feedback visible on entry |
| T5 | Create a goal for a student (from student detail or goals UI) | Goal on student view |
| T6 | Post announcement in **Group** | Appears in group feed |
| T7 | (Optional) `/accounts/cohorts/` — open cohort/group | Admin/teacher cohort UI loads |

### Tasks — admin (optional 6th session)

| # | Task | Success criteria |
|---|------|------------------|
| A1 | `/accounts/users/` — create or import a test user | User exists |
| A2 | Assign student to cohort/group | Student sees correct group on dashboard |

---

## Observation checklist

Per task note:

- Completed independently? (Yes / With hint / Failed)
- Rough time on task
- Confusion, hesitation, backtracking
- Spoken reactions; error messages

---

## Severity rating

| Rating | Meaning |
|--------|---------|
| Critical | Task blocked; core usage impossible |
| High | Completed with major difficulty or errors |
| Medium | Minor confusion; quick workaround |
| Low | Cosmetic |

---

## Post-session questions (5 min)

1. Most confusing part?
2. What felt natural?
3. Anything expected but missing?
4. Compared to tools you use (Notion, Google Docs, …)?
5. Would you use this regularly? Why / why not?

---

## Findings template

| ID | Task | Severity | Description | Quote / observation | Recommended fix |
|----|------|----------|-------------|---------------------|-------------------|
| F01 | T2 | Medium | Share toggle not noticed | "I didn't know teachers could see it" | Stronger label on visibility |
| … | | | | | |

---

## Acceptance threshold

- ≥5 sessions completed
- All **Critical** issues resolved before launch
- All **High** issues have a documented fix plan
- Results recorded below; teaching team sign-off

---

## Results

_To be filled after sessions._

### Session log

| Date | Participant | Role | Tasks completed | Key findings |
|------|-------------|------|-----------------|--------------|
| | | | | |

### Summary of findings

_(Findings table)_

### Sign-off

- [ ] ≥5 sessions completed
- [ ] All Critical resolved
- [ ] All High have fix plan
- [ ] Teaching team reviewed
- [ ] Next steps in [TODO.md](TODO.md) or issue tracker
