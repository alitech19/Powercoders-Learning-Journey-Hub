# Authentication roadmap (integration branch)

Phased port of security features from the Ali branch.

## Dev quick login vs normal login

| Path | Behaviour |
|------|-----------|
| **Quick login buttons** | Direct session; seed users have DB flags set to skip onboarding/security gates |
| **Email + password form** | Full production auth flow (axes lockout, 2FA, privacy, password change, …) |

## Phases

| Phase | Status | Scope |
|-------|--------|--------|
| **A** | Done | deps, Argon2, axes, CSP headers, OTP apps installed |
| **B** | Done | two_factor URLs, login templates, `LOGIN_URL` switch, Tailwind CDN login UI |
| **C** | Done | axes username callable (auth- prefix + credentials), per-user lockout, Ali lockout UI, EmailLoginView |
| **D** | Done | User security fields + `AuditLog`; seed sets bypass flags |
| **E** | Done | middleware: privacy, password change, require 2FA (staff), audit log; dev quick-login 2FA bypass |
| **F** | Done | welcome view/template + `WelcomeMiddleware` |
| **G** | Done | sessions in Redis, structured JSON logging |

**Auth roadmap complete (A–G).** Next: business apps (`dashboard`, …).

## Seed user bypass fields (Phase D)

Set on all users created by `seed_dev_data` and `create_dev_superuser`:

- `privacy_policy_accepted=True`
- `welcome_seen=True`
- `must_change_password=False`

Staff seed users: dev quick-login sets session `dev_auth_bypass` to skip 2FA setup when `ENABLE_DEV_SEED` is on. Normal form login still requires 2FA for staff.
