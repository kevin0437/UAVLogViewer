# UAV Log Viewer Chatbot

A conversational chatbot extension for UAV Log Viewer that allows users to ask questions about MAVLink, DataFlash, and DJI OSD telemetry logs. It provides deterministic metric-based answers for core flight statistics and uses a large language model (LLM) for investigative queries.

## Features

- **Client-side parsing** of `.tlog`, `.bin`, and `.txt` logs via Web Worker
- **Filtered data extraction** for key fields across three formats (DataFlash, DJI OSD, MAVLink)
- **Deterministic metrics** for:
  - Highest altitude (and timestamp)
  - Battery temperature extremes
  - Total flight time
  - GPS losses and fix status
  - RC signal metrics
  - Critical errors and timestamps
- **Natural-language summary** generated once per upload using a cost‑effective LLM (gpt-3.5-turbo)
- **Conversational chat** powered by a more capable model (gpt-4o-mini) with:
  - Short-circuited metric queries (instant, accurate responses)
  - Flexible reasoning for anomalies and investigative questions
  - Conversation history for context-aware dialogue

## Architecture Overview

```
Frontend (Vue.js)
  ├─ Dropzone component parses logs → emits sessionStarted
  ├─ Sidebar.vue listens, obtains sessionId, renders chat UI
  └─ Chat UI calls /api/chat for questions

Backend (FastAPI)
  ├─ /upload_log: flatten → filter → compute_metrics → LLM summary → return session_id + summary
  ├─ /chat: short-circuit metrics OR LLM chat with summary + history → return reply
  └─ In-memory session store for raw data, filtered, metrics, summary, history
```

## Prerequisites

- Node.js ≥14 and npm/yarn
- Python 3.9+ and virtualenv
- OpenAI API key
## Frontend Setup

    ```bash
    npm install
    # serve with hot reload at localhost:8080
    npm run dev
    ```

## Backend Setup

1. Create and activate a virtual environment:
   ```bash
   cd uavlogviewer/backend
   python -m venv .venv
   source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Add your OpenAI key to `.env`:
   ```dotenv
   OPENAI_API_KEY=sk-...
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn app:app --reload --port 8000
   ```

## Endpoints

- **`GET /health`** — Returns `{"status":"ok"}`
- **`POST /upload_log`** — Accepts full telemetry JSON; returns `{ session_id, summary }`
- **`POST /chat`** — Accepts `{ session_id, message }`; returns `{ reply }`

## Usage

1. Upload a parsed log via the front end.
2. Receive a session ID and a human-readable summary.
3. Enter questions in the chat box, e.g.:
   - "What was the highest altitude reached during the flight?"
   - "When did the GPS signal first get lost?"
   - "Can you spot any issues in the GPS data?"
4. Metric queries return immediate, exact numbers; investigative queries use the LLM summary for reasoning.

## Key Filtered Fields

| Format    | Raw Field                          | Filtered Key           |
| --------- | ---------------------------------- | ---------------------- |
| DataFlash | `GPS[0].Alt`                       | `gps_altitude`         |
| DataFlash | `GPS[0].TimeUS`                    | `gps_time`             |
| DataFlash | `GPS[0].Status`                    | `gps_status`           |
| DataFlash | `STAT.BTemp`                       | `battery_temp`         |
| DataFlash | `MSG.Message`                      | `msg_messages`         |
| DataFlash | `MSG.TimeUS`                       | `msg_time`             |
| DJI OSD   | `OSD.altitude`                     | `altitude`             |
| DJI OSD   | `OSD.flyTime`                      | `flight_time`          |
| DJI OSD   | `BATTERY.temperature`              | `battery_temperature`  |
| DJI OSD   | `OSD.nonGpsCause`                  | `gps_loss_reason`      |
| DJI OSD   | `RC.downlinkSignal`                | `rc_downlink_signal`   |
| DJI OSD   | `RC.uplinkSignal`                  | `rc_uplink_signal`     |
| MAVLink   | `GLOBAL_POSITION_INT.alt`          | `absolute_altitude_mm` |
| MAVLink   | `GLOBAL_POSITION_INT.relative_alt` | `relative_altitude_m`  |
| MAVLink   | `GPS_RAW_INT.fix_type`             | `gps_fix_type`         |
| MAVLink   | `SYSTEM_TIME.time_unix_usec`       | `start_time_unix`      |
| MAVLink   | `RC_CHANNELS_RAW.rssi`             | `rc_signal_strength`   |
| MAVLink   | `STATUSTEXT.text`                  | `status_texts`         |

## License

MIT License © Your Name
