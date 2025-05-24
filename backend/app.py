from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Body, HTTPException
from state import new_session, get_session
from typing import List, Dict, Any, Optional
from fastapi import File, UploadFile, Body, HTTPException, Request

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from datetime import timedelta

load_dotenv() 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    session_id: str
    message: str
    
def find_useful_DataFlash(flat):
    useful_info = {}

    # Define expected keys and their short names for result
    key_map = {
        # DataFlash keys
        "GPS[0].Alt": "gps_altitude",
        "GPS[0].TimeUS": "gps_time",
        "GPS[0].Status": "gps_status",
        "STAT.BTemp": "battery_temp",
        "MSG.Message": "msg_messages",
        "MSG.TimeUS": "msg_time",
        # DJI OSD keys
        "OSD.altitude": "altitude",
        "OSD.flyTime": "flight_time",
        "BATTERY.temperature": "battery_temperature",
        "OSD.nonGpsCause": "gps_loss_reason",
        "RC.downlinkSignal": "rc_downlink_signal",
        "RC.uplinkSignal": "rc_uplink_signal",
        # MAVLink keys
        "GLOBAL_POSITION_INT.alt": "absolute_altitude_mm",
        "GLOBAL_POSITION_INT.relative_alt": "relative_altitude_m",
        "GPS_RAW_INT.fix_type": "gps_fix_type",
        "SYSTEM_TIME.time_unix_usec": "start_time_unix",
        "RC_CHANNELS_RAW.rssi": "rc_signal_strength",
        "STATUSTEXT.text": "status_texts"
    }

    # Extract only present keys
    for flat_key, label in key_map.items():
        if flat_key in flat:
            useful_info[label] = flat[flat_key]

    return useful_info

# Compute deterministic metrics using filtered keys
def compute_metrics(filtered: Dict[str, Any]) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}

    # Altitude: try GPS, then DJI, then MAVLink
    alt_keys = ["gps_altitude", "altitude", "absolute_altitude_mm", "relative_altitude_m"]
    time_map = {k: "gps_time" for k in alt_keys}
    for key in alt_keys:
        if key in filtered:
            alts = filtered.pop(key) or []
            time_key = "gps_time"
            times = filtered.pop(time_key, [])
            if alts:
                max_alt = max(alts)
                idx = alts.index(max_alt)
                metrics[key] = max_alt if key != "absolute_altitude_mm" else max_alt / 1000
            break

    # Battery temperature extremes
    batt_keys = ["battery_temp", "battery_temperature"]
    for key in batt_keys:
        if key in filtered:
            vals = filtered.pop(key) or []
            if vals:
                metrics["max_battery_temp"] = max(vals)
                metrics["min_battery_temp"] = min(vals)
            break

    # Flight time
    if "flight_time" in filtered:
        metrics["flight_time"] = filtered.pop("flight_time")
    if "start_time_unix" in filtered:
        start_time = filtered["start_time_unix"][0][0]
        end_time = filtered["start_time_unix"][-1][0]
        metrics["flight_time"] = end_time - start_time
        filtered.pop("start_time_unix")

    # GPS loss info
    if "gps_loss_reason" in filtered:
        metrics["gps_loss_reasons"] = filtered.pop("gps_loss_reason")
    if "gps_status" in filtered:
        metrics["gps_status_list"] = filtered.pop("gps_status")
    if "gps_fix_type" in filtered:
        metrics["gps_fix_type"] = filtered.pop("gps_fix_type")

    # RC signal metrics
    for key in ["rc_downlink_signal", "rc_uplink_signal", "rc_signal_strength"]:
        if key in filtered:
            metrics[key] = filtered.pop(key)

    # Error messages and timestamps
    if "msg_messages" in filtered:
        metrics["critical_errors"] = filtered.pop("msg_messages")
    if "msg_time" in filtered:
        metrics["error_times"] = filtered.pop("msg_time")

    # Status texts (warnings/info)
    if "status_texts" in filtered:
        metrics["status_texts"] = filtered.pop("status_texts")

    return metrics, filtered
    
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/upload_log")
async def upload_log(
    request: Request,
    file: Optional[UploadFile] = File(None)
) -> Dict[str, Any]:

    telemetry = await request.json()
    flat: Dict[str, Any] = {}
    for msg_type, payload in telemetry.items():
        if isinstance(payload, dict):
            # payload is a dict of field→array
            for field_name, arr in payload.items():
                key = f"{msg_type}.{field_name}"
                flat[key] = arr
        else:
            # in case some top‐level values are already arrays
            flat[msg_type] = payload
            
    filtered = find_useful_DataFlash(flat)
    filtered_text = json.dumps(filtered, indent=2)
    session_id = new_session(filtered)
    sess = get_session(session_id)
    sess["filtered"] = filtered
    sess.setdefault("history", [])
    metrics,filtered_info = compute_metrics(filtered)
    
    sess["metrics"] = metrics
    sess["filtered_info"] = filtered_info
    
    return {"session_id": session_id, "filtered_info": filtered_info}


@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    # Retrieve session
    sess = get_session(request.session_id)
    if not sess:
        raise HTTPException(404, "Session not found")

    user_msg = request.message
    lower = user_msg.lower()
    metrics = sess.get("metrics", {})


    # 2) Otherwise, fall back to LLM with a clear system prompt
    summary = sess.get("filtered_info", "")
    history = sess.setdefault("history", [])

    system_prompt = (
        "You are a UAV log analyst.\n"
        "Use the following pre-computed metrics and data to answer questions accurately:\n\n"
        f"Metrics:\n{json.dumps(metrics, indent=2)}\n\n"
        f"data:\n{json.dumps(summary, indent=2)}\n\n"
        "If you can find the answer in the metrics, do so directly.\n"
        "If you cannot, use the data to answer the question.\n"
        "If the question is about a specific time, use the data to find the relevant point.\n"
        "If the question is about a range of times, summarize the data for that range.\n"
        "If the question is about a specific event, use the data to find it.\n"
        "If the question is about a trend or pattern, summarize the data over time.\n"
        "For investigative or anomaly questions, draw on the data and your expertise."
    )

    messages = [{"role": "system", "content": system_prompt}]
    # replay history
    for turn in history:
        messages.append({"role": "user",      "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    # add current user question
    messages.append({"role": "user", "content": user_msg})

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500
        )
        reply = resp.choices[0].message.content.strip()
    except openai_error.OpenAIError as e:
        raise HTTPException(502, f"Chat API error: {e}")

    # save and return
    history.append({"user": user_msg, "assistant": reply})
    return {"reply": reply}
