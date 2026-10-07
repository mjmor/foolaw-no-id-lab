# No-ID Lab Evidence Schema

## Purpose

This schema defines the minimum metadata needed to make an observation reproducible, comparable across apps, and useful for statutory analysis.

## Required fields

| Field | Type | Description |
|---|---|---|
| `observation_id` | string | Stable unique identifier |
| `platform` | enum | `android_emulator`, `android_physical`, `ios_physical`, or `web` |
| `app` | string | App name |
| `app_version` | string | Installed app version |
| `os_version` | string | Device OS version |
| `persona` | string | Synthetic persona identifier |
| `parental_control_profile` | string | Control profile name |
| `parental_control_state` | object | Exact settings captured before the observation |
| `local_time` | ISO timestamp | Local device time |
| `time_window` | enum | Morning, school hours, after school, evening, or overnight |
| `age_signal` | object | Age or minor-status signals observed or inferred |
| `engagement_mechanism` | string | Notification, recommendation, feed surface, prompt, or contact signal |
| `notification` | object | Notification category, content, delivery time, and recipient |
| `content_filter` | object | Filter state, who can change it, and whether it is default |
| `contact_signal` | object | Outside-network contact prompt or request behavior |
| `evidence_artifact` | path | Reference to a raw capture stored outside Git |
| `statute_hook` | string | Statutory research question or provision label |
| `notes` | string | Context needed to interpret the observation |

## Suggested record format

```yaml
observation_id: android-emulator-youtube-minor-a-001
platform: android_emulator
app: YouTube
app_version: 1.2.3
os_version: Android 15
persona: minor_a_12
parental_control_profile: supervised_account
parental_control_state:
  supervised_account: true
  content_restrictions: enabled
local_time: "2026-10-07T18:30:00-04:00"
time_window: evening
age_signal:
  declared_age: 12
  inferred_minor: true
engagement_mechanism: recommendation_prompt
notification:
  sent_to: minor
  category: recommendation
content_filter:
  restricted_mode: enabled
  changeable_by_minor: false
contact_signal: null
evidence_artifact: captures/2026-10-07/android-youtube-001.png
statute_hook: engagement_feature_minor_use
notes: Example record only.
```

## Storage model

- Raw artifacts such as screenshots, videos, and logs stay outside Git.
- Structured summaries can be stored as JSONL or SQLite records.
- Derived matrices and reports should be regenerated from structured records.
- Each record must reference its raw evidence artifact.

## Validation rules

- Every observation must have an ID and local timestamp.
- `platform` must identify whether the result came from an emulator or physical device.
- `parental_control_state` must be captured before the observation.
- `statute_hook` must map to a defined research question.
- Raw evidence must remain outside the Git repository.
