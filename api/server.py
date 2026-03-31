"""T78 Training Coach API — FastAPI backend proxying to Claude."""

import json
from datetime import date
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()
client = anthropic.AsyncAnthropic()

DATA_PATH = Path("/app/data/training.json")
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


def build_system_prompt() -> str:
    """Build system prompt with current training data."""
    data = json.loads(DATA_PATH.read_text())

    race_date = date.fromisoformat(data["race"]["date"])
    today = date.today()
    days_to_race = (race_date - today).days

    # Find current phase
    plan_start = date.fromisoformat(data["plan_start"])
    current_week = min(max((today - plan_start).days // 7 + 1, 0), 14)
    phase = "Pre-training"
    for p in data.get("phases", []):
        if current_week in p["weeks"]:
            phase = p["name"]
            break

    return f"""You are the T78 Coach, a knowledgeable and motivating trail running training advisor. \
You are helping an athlete prepare for the Swiss Iron Trail T78 — a 78 km mountain race with \
5,000 m of elevation gain in Savognin, Switzerland on June 27, 2026. The cutoff is 21 hours.

Today is {today.isoformat()}. The race is in {days_to_race} days. Current training week: {current_week} of 14. Phase: {phase}.

You have the athlete's complete training data below. Use it to give specific, actionable advice. \
Reference actual numbers — distances, paces, heart rates, elevation — when relevant. \
Compare planned vs actual training when the athlete asks about progress. \
Be encouraging but honest about gaps. Keep responses concise and practical.

## Race Details
{json.dumps(data["race"], indent=2)}

## Upcoming Events
{json.dumps(data.get("events", []), indent=2)}

## 14-Week Training Plan (targets per week)
{json.dumps(data.get("plan", []), indent=2)}

## Actual Training Completed
{json.dumps(data.get("actual", []), indent=2)}

## Time Prediction & Reference Races
{json.dumps(data.get("prediction", {}), indent=2)}

## Exercise Program
{json.dumps(data.get("exercises", {}), indent=2)}

## Course Profile & Waypoints
{json.dumps(data.get("course_profile", {}), indent=2)}

## Dike Training (local hill repeats)
{json.dumps(data.get("dike_training", {}), indent=2)}

Guidelines:
- Give specific, actionable advice referencing the athlete's actual data
- Compare planned vs actual when discussing progress
- Be encouraging but honest about gaps or risks
- Reference specific weeks, sessions, distances, and paces
- For nutrition/pacing questions, use the race data and course profile
- Consider the current date and days to race when prioritizing advice
- Use metric units (km, m, min/km)
- Format responses with markdown for readability"""


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Stream a coaching response."""
    try:
        system = build_system_prompt()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Training data not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load training data: {e}")

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    async def generate():
        async with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
