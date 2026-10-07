# No-ID Lab Research Plan

## Goal

Survey age signals, kids' engagement mechanisms, and parental-control configurations across major apps to help Colorado and Connecticut attorneys general determine whether current statutory definitions adequately cover engagement signals intended to keep minors on a platform.

## Research questions

1. What age and minor-status signals do apps collect or infer under each persona?
2. Which parental-control settings are available for each app and platform?
3. How do push notifications and recommendations change across parental-control profiles?
4. What default content filters and algorithmic surfaces are presented to minors?
5. How do delivery interfaces such as Shorts, Reels, Stories, posts, and live chat vary by profile?
6. What parental notifications or outside-network contact signals are present?
7. How do these observations vary by time of day and platform?

## Apps in scope

| App | Platform priority | Notes |
|---|---|---|
| YouTube | Android first, iOS validation | Includes YouTube Kids and supervised YouTube if applicable |
| Instagram | Android first, iOS validation | Includes teen account controls and Family Center features |
| Facebook | Android first, iOS validation | Includes Messenger and Family Center features where relevant |
| Snapchat | Android first, iOS validation | Includes parental tools and family center features |
| TikTok | Android first, iOS validation | Includes Family Pairing and teen safety features |
| Kick | Android first, iOS validation | Prioritize live chat, recommendations, and notification behavior |

## Personas

| Persona | Age | Purpose |
|---|---|---|
| Minor A | 12 | Younger-child app and content behavior |
| Minor B | 15 | Teen app and engagement behavior |
| Parent A | Adult | Default parental-control configuration |
| Parent B | Adult | Restrictive parental-control configuration |

Additional persona details should be stored in `configs/personas/` once the investigation begins. Personas must be synthetic or approved test accounts.

## Parental-control profiles

| Profile | Description |
|---|---|
| None/default | No parental control or supervision enabled |
| Supervised account | Minor account is linked to an adult account |
| Content restrictions | Age-appropriate or restricted content filters enabled |
| Contact restrictions | Unknown-contact or outside-network contact limits enabled |
| Time limits | Usage or screen-time limits enabled |
| Notification limits | Push notifications or notification scheduling restricted |
| Combined restrictive | Multiple controls enabled together |

Each app observation should record which controls are available, unavailable, partially configurable, or enforced by default.

## Observation windows

| Window | Hours |
|---|---|
| Morning | 6:00–8:59 local time |
| School hours | 9:00–14:59 local time |
| After school | 15:00–17:59 local time |
| Evening | 18:00–21:59 local time |
| Overnight | 22:00–5:59 local time |

All observations should record local time and the relevant statutory jurisdiction assumption.

## Evidence categories

### Age signals

Record visible age declarations, inferred age categories, supervised-account state, parental linkage, age-related permissions, and any signals the app sends or requests that indicate minor status.

### Push notifications

Record notification content, frequency, category, time of day, and whether it changes with parental-control configuration.

### Recommended kid-friendly settings

Record prompts, suggestions, or onboarding screens that recommend safety, privacy, or engagement settings for minors.

### Default content filters

Record the initial state of content filters, restricted modes, NSFW controls, and whether a filter can be changed by the minor or requires parental approval.

### Algorithmic content and delivery interfaces

Record the types of content surfaced and the delivery mechanism, such as posts, Reels, Shorts, Stories, live feeds, chat prompts, or recommendations. Capture the visible surface without collecting personal data.

### Parental notifications

Record notifications sent to a linked parent account, including their content, timing, and trigger.

### Contact from outside network

Record contact requests, connection prompts, friend suggestions, live-chat prompts, or messages from outside the minor's network. Do not initiate contact with real users.

## Statute mapping

Colorado and Connecticut analysis should map each observation to the relevant statutory hooks, including:

- Duty of care for minors
- Restrictions on engagement features that increase, sustain, or extend minors' use
- Limits on unsolicited contact
- Age verification or minor-status signals
- Parental-control and disclosure requirements

Each evidence record should include a `statute_hook` field so observations can be grouped by statutory concern.

## Automation sequence

1. Build the evidence schema and configuration format.
2. Automate Android emulator setup and app installation.
3. Capture UI, notification, and settings state.
4. Add physical iPhone validation for iOS-specific behavior.
5. Add a physical Android validation tier.
6. Generate per-app and per-control matrices.
7. Produce statutory analysis summaries.

## Ethics and review constraints

- Use synthetic personas or approved test accounts.
- Do not collect data from real minors.
- Do not circumvent authentication, age gates, or parental controls.
- Store raw evidence outside Git.
- Coordinate evidence handling and publication with legal and AG partners.
