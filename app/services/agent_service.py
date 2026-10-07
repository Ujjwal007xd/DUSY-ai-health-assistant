"""AI Health Agent Service — Context-Aware Personalized Health Intelligence.

Pipeline Architecture:
UNDERSTAND → RETRIEVE → PROBE → SAFETY_CHECK → ANALYZE → ACT → STORE → FOLLOW UP
"""

import json
from datetime import datetime
from bson import ObjectId
from typing import Optional

from google import genai
from google.genai import types
from fastapi import HTTPException, status

from app.config import get_settings
from app.database import get_database
from app.models.agent import (
    AgentInteractRequest, AgentResponse, AgentThoughtStep,
    AgentActionItem, AgentContextResponse, AgentActionExecutionRequest,
    AgentConsultationSummary
)

AVAILABLE_GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite"
]

AGENT_SYSTEM_PROMPT = """You are DUSY, the Personalized Clinical Intelligence Agent.
You are NOT a basic chatbot. You are an autonomous, interactive clinical intelligence agent that provides personalized health assessments, conducts step-by-step intake triage, checks for safety red flags, and formulates measurable health goals.

MULTI-TURN CONVERSATION STAGES:
Evaluate the user query and recent conversation to determine the correct stage:

1. STAGE "intake":
- If the user describes a new symptom or answers an initial intake question:
- Acknowledge their symptom empathetically.
- If key details are missing (duration, frequency, intensity 1-10, or location/triggers), ask 1 or 2 focused questions.
- ALWAYS provide 3-5 clickable "quick_replies" choice chips.
  Examples:
  - For duration: ["Around two weeks", "A few days", "Over a month", "Just started yesterday"]
  - For frequency: ["Once a week", "2–3 times a week", "Almost every day", "Several times a day"]
  - For intensity: ["Mild (1–3)", "Moderate (4–6)", "Severe (7–10)"]
  - For location: ["Front of head / forehead", "Around the eyes", "Back of neck / shoulders", "Other"]

2. STAGE "safety_screen":
- When the user has answered the main intake questions (duration, frequency, intensity, location), BEFORE providing final guidance:
- You MUST screen for emergency signs.
- Message:
  "Thank you. Before continuing, I need to check for symptoms that may require prompt medical attention. Are you experiencing any of the following?
  - Sudden, unusually severe pain or headache
  - High fever or stiff neck
  - Vision changes, speech difficulty, or weakness/numbness
  - Difficulty breathing or chest pressure"
- Provide quick_replies: ["No, none of those", "Yes, I have symptoms"]

3. STAGE "guidance":
- When the user confirms "No, none of those" (or red flags cleared):
- Say: "Good, that helps rule out immediate red flags."
- Deliver a comprehensive, structured, personalized assessment incorporating their ACTUAL profile context (BMI, sleep hours, exercise, water intake, stress level, allergies, medical conditions).
- Explain potential causes (e.g. tension headache, muscle strain/DOMS, dehydration, ergonomic strain).
- Provide practical at-home relief steps.
- Offer 4 interactive next actions in "suggested_actions":
  1. {"action_type": "health_log", "title": "📋 Save Assessment", "description": "Save this assessment to your ongoing health tracking log.", "payload": {"status": "saved"}}
  2. {"action_type": "create_goal", "title": "🎯 Create Health Goals", "description": "Generate 3 tailored habit goals based on your profile.", "payload": {"target": "recovery_goals"}}
  3. {"action_type": "lifestyle_tweak", "title": "📊 Analyze Lifestyle Factors", "description": "Review sleep, hydration, and stress correlations.", "payload": {"category": "lifestyle"}}
  4. {"action_type": "screening_alert", "title": "📝 Doctor Visit Summary", "description": "Generate a concise briefing to share with your physician.", "payload": {"type": "doctor_summary"}}
- Provide quick_replies: ["🎯 Create Health Goals", "📋 Save Assessment", "📊 Analyze Lifestyle Factors", "📝 Doctor Visit Summary"]

4. STAGE "goals":
- If the user chooses "🎯 Create Health Goals" or asks to create goals:
- Formulate 3 specific, measurable health goals customized to their exact condition and lifestyle numbers (e.g. 1. Sleep: aim for 7.5-8h; 2. Hydration: reach 2.5L daily; 3. Ergonomics / 15-min daily mobility).
- Put these 3 goals into "suggested_actions" (action_type: "create_goal").
- Provide quick_replies: ["Create All Goals", "Modify Goals"]

5. STAGE "completed":
- If the user clicks or says "Create All Goals":
- Confirm:
  "✓ Assessment saved to your health history\n✓ 3 health goals created and tracked\nAll data is stored in your profile. You can review your active goals below or in your Health Dashboard."
- Provide quick_replies: ["Ask another health question", "Review My Goals"]

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this schema:
{
  "stage": "intake" | "safety_screen" | "guidance" | "goals" | "completed",
  "pipeline_steps": [
    {"stage": "RETRIEVE", "detail": "Retrieved user profile..."},
    {"stage": "PROBE", "detail": "Checked duration, frequency, intensity..."},
    {"stage": "SAFETY_CHECK", "detail": "Screened for red flags..."},
    {"stage": "ANALYZE", "detail": "Correlated symptoms with lifestyle..."},
    {"stage": "ACT", "detail": "Proposed clinical action steps..."}
  ],
  "agent_message": "Structured, empathetic response text",
  "quick_replies": ["Choice 1", "Choice 2", "Choice 3"],
  "missing_questions": ["Question 1 if any"],
  "red_flags": [],
  "suggested_actions": [
    {
      "action_type": "create_goal",
      "title": "Action Title",
      "description": "Short explanation",
      "payload": {}
    }
  ]
}
"""


async def get_agent_health_context(user_id: str, user: dict) -> AgentContextResponse:
    """Retrieve and aggregate all available user health records into a single context."""
    db = get_database()
    
    # 1. Profile
    profile = await db.health_profiles.find_one({"user_id": user_id})
    
    # 2. Latest Preventive Lifestyle Analysis
    preventive = await db.preventive_analyses.find_one(
        {"user_id": user_id},
        sort=[("generated_at", -1)]
    )
    
    # 3. Consultations count
    consult_count = await db.agent_consultations.count_documents({"user_id": user_id})

    # Check available fields
    has_profile = profile is not None
    has_medical_conditions = bool(profile and profile.get("medical_conditions"))
    has_medications = bool(profile and profile.get("current_medications"))
    has_lifestyle = bool(preventive and preventive.get("lifestyle_data"))
    has_history = consult_count > 0 or bool(profile and profile.get("family_history"))

    # Compute completion percentage
    score = 0
    if has_profile: score += 25
    if profile and profile.get("height_cm") and profile.get("weight_kg"): score += 20
    if has_medical_conditions or has_medications: score += 20
    if has_lifestyle: score += 25
    if has_history: score += 10
    completion_percentage = min(score, 100)

    profile_summary = {}
    if profile:
        profile_summary = {
            "height_cm": profile.get("height_cm"),
            "weight_kg": profile.get("weight_kg"),
            "bmi": profile.get("bmi"),
            "bmi_category": profile.get("bmi_category"),
            "blood_group": profile.get("blood_group"),
            "medical_conditions": profile.get("medical_conditions", []),
            "allergies": profile.get("allergies", []),
            "current_medications": profile.get("current_medications", []),
            "family_history": profile.get("family_history", [])
        }

    lifestyle_summary = {}
    if preventive and preventive.get("lifestyle_data"):
        lifestyle_summary = preventive.get("lifestyle_data")

    return AgentContextResponse(
        user_id=user_id,
        user_name=user.get("name", "User"),
        completion_percentage=completion_percentage,
        has_profile=has_profile,
        has_medical_conditions=has_medical_conditions,
        has_medications=has_medications,
        has_lifestyle=has_lifestyle,
        has_history=has_history,
        profile_summary=profile_summary,
        lifestyle_summary=lifestyle_summary,
        recent_consultations_count=consult_count
    )


def _check_critical_red_flags(query: str) -> list[str]:
    """Deterministic clinical red-flag symptom screening."""
    q = query.lower()
    flags = []
    
    if any(k in q for k in ["chest pain", "pressure in chest", "left arm pain", "radiating to jaw"]):
        flags.append("Possible acute coronary or cardiovascular distress — seek emergency medical evaluation immediately.")
    if any(k in q for k in ["thunderclap", "worst headache of my life", "sudden severe headache"]):
        flags.append("Sudden explosive severe headache — requires emergency evaluation for neurological events.")
    if any(k in q for k in ["slurred speech", "face drooping", "arm weakness", "can't move one side"]):
        flags.append("FAST Stroke indicators detected — call emergency services immediately.")
    if any(k in q for k in ["coughing blood", "difficulty breathing", "cannot breathe", "stridor"]):
        flags.append("Severe respiratory compromise detected.")
    if any(k in q for k in ["stiff neck with fever", "stiff neck high fever", "neck stiffness and fever"]):
        flags.append("Signs concerning for meningeal irritation — requires urgent physician assessment.")
        
    return flags


async def interact_with_agent(
    request: AgentInteractRequest, user: dict
) -> AgentResponse:
    """Execute the Agentic Intelligence Pipeline."""
    db = get_database()
    settings = get_settings()
    user_id = user["_id"] if isinstance(user["_id"], str) else str(user["_id"])

    # ─── 1. UNDERSTAND & RETRIEVE CONTEXT ───
    context_data = await get_agent_health_context(user_id, user)
    
    # Check for active consultation or initialize new one
    consultation = None
    if request.consultation_id:
        try:
            consultation = await db.agent_consultations.find_one({
                "_id": ObjectId(request.consultation_id),
                "user_id": user_id
            })
        except Exception:
            consultation = None

    if not consultation:
        previous_consults = await db.agent_consultations.find(
            {"user_id": user_id}
        ).sort("updated_at", -1).limit(3).to_list(3)

        consultation = {
            "user_id": user_id,
            "task_type": request.task_type or "symptom_assessment",
            "title": f"{request.task_type.replace('_', ' ').title()}: {request.message[:35]}...",
            "messages": [],
            "previous_consults_summary": [c.get("title") for c in previous_consults],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        res = await db.agent_consultations.insert_one(consultation)
        consultation_id = str(res.inserted_id)
        consultation["_id"] = res.inserted_id
    else:
        consultation_id = str(consultation["_id"])

    # ─── 2. SAFETY RED FLAG CHECK ───
    deterministic_red_flags = _check_critical_red_flags(request.message)

    # ─── 3. BUILD AGENT REASONING CONTEXT ───
    user_context_str = f"""
USER PROFILE CONTEXT:
- Name: {user.get('name', 'User')}
- Gender: {user.get('gender', 'Not specified')}
- Date of Birth: {user.get('date_of_birth', 'Not specified')}
- Height: {context_data.profile_summary.get('height_cm', 'Not specified')} cm
- Weight: {context_data.profile_summary.get('weight_kg', 'Not specified')} kg
- BMI: {context_data.profile_summary.get('bmi', 'Not calculated')} ({context_data.profile_summary.get('bmi_category', '')})
- Blood Group: {context_data.profile_summary.get('blood_group', 'Not specified')}
- Known Medical Conditions: {', '.join(context_data.profile_summary.get('medical_conditions', [])) or 'None recorded'}
- Known Allergies: {', '.join(context_data.profile_summary.get('allergies', [])) or 'None recorded'}
- Current Medications: {', '.join(context_data.profile_summary.get('current_medications', [])) or 'None recorded'}
- Family History: {', '.join(context_data.profile_summary.get('family_history', [])) or 'None recorded'}

LIFESTYLE DATA:
- Sleep Hours: {context_data.lifestyle_summary.get('sleep_hours', 'Not logged')}
- Daily Exercise: {context_data.lifestyle_summary.get('exercise_minutes_per_day', 'Not logged')} min
- Daily Steps: {context_data.lifestyle_summary.get('daily_steps', 'Not logged')}
- Water Intake: {context_data.lifestyle_summary.get('water_intake_liters', 'Not logged')} L
- Diet Type: {context_data.lifestyle_summary.get('diet_type', 'Not logged')}
- Stress Level: {context_data.lifestyle_summary.get('stress_level', 'Not logged')}
- Smoker: {context_data.lifestyle_summary.get('smoking', 'No')}

PREVIOUS CONSULTATION TOPICS ON RECORD:
{json.dumps(consultation.get('previous_consults_summary', []))}

CURRENT TASK: {request.task_type}
USER QUERY: {request.message}
"""

    history_str = ""
    recent_msgs = consultation.get("messages", [])[-8:]
    if recent_msgs:
        history_str = "\nRECENT CONVERSATION IN THIS CONSULTATION:\n"
        for m in recent_msgs:
            history_str += f"- {m['role'].upper()}: {m['content']}\n"

    full_prompt = f"{AGENT_SYSTEM_PROMPT}\n{user_context_str}\n{history_str}\nProvide the Agentic JSON response."

    # ─── 4. REASONING CALL (WITH MULTI-MODEL FALLBACK) ───
    thought_steps = [
        AgentThoughtStep(stage="UNDERSTAND", detail=f"Categorized task as {request.task_type}."),
        AgentThoughtStep(stage="RETRIEVE", detail=f"Loaded user profile (BMI: {context_data.profile_summary.get('bmi', 'N/A')}), lifestyle data, and history."),
        AgentThoughtStep(stage="SAFETY_CHECK", detail="Screened for acute red flags and emergency symptoms.")
    ]
    missing_questions = []
    quick_replies = []
    red_flags = list(deterministic_red_flags)
    suggested_actions = []
    agent_message = ""
    stage = "intake"

    success = False
    if settings.GEMINI_API_KEY:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        for model_name in AVAILABLE_GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                        max_output_tokens=3000,
                    )
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_text = "\n".join(lines).strip()
                
                parsed = json.loads(raw_text)
                agent_message = parsed.get("agent_message", "")
                stage = parsed.get("stage", "intake")
                quick_replies = parsed.get("quick_replies", [])
                
                for step in parsed.get("pipeline_steps", []):
                    thought_steps.append(AgentThoughtStep(
                        stage=step.get("stage", "ANALYZE"),
                        detail=step.get("detail", "")
                    ))
                
                missing_questions = parsed.get("missing_questions", [])
                for rf in parsed.get("red_flags", []):
                    if rf not in red_flags:
                        red_flags.append(rf)
                
                for act in parsed.get("suggested_actions", []):
                    suggested_actions.append(AgentActionItem(
                        action_type=act.get("action_type", "health_log"),
                        title=act.get("title", "Action"),
                        description=act.get("description", ""),
                        payload=act.get("payload", {})
                    ))
                
                success = True
                break
            except Exception as err:
                print(f"Gemini call to {model_name} failed: {err}")
                continue

    if not success:
        fb = _smart_fallback_engine(request, context_data, consultation.get("messages", []))
        agent_message = fb["message"]
        stage = fb["stage"]
        quick_replies = fb["quick_replies"]
        missing_questions = fb["missing_questions"]
        suggested_actions = fb["suggested_actions"]
        for step in fb["thought_steps"]:
            thought_steps.append(step)

    # ─── 5. PERSIST CONSULTATION & LOGS ───
    now = datetime.utcnow()
    user_msg_entry = {"role": "user", "content": request.message, "timestamp": now}
    agent_msg_entry = {
        "role": "agent",
        "content": agent_message,
        "stage": stage,
        "thought_pipeline": [s.model_dump() for s in thought_steps],
        "quick_replies": quick_replies,
        "missing_questions": missing_questions,
        "red_flags": red_flags,
        "suggested_actions": [a.model_dump() for a in suggested_actions],
        "timestamp": now
    }

    await db.agent_consultations.update_one(
        {"_id": ObjectId(consultation_id)},
        {
            "$push": {"messages": {"$each": [user_msg_entry, agent_msg_entry]}},
            "$set": {
                "updated_at": now,
                "task_type": request.task_type
            }
        }
    )

    # If completed stage, also auto-record the 3 goals in agent_actions collection
    if stage == "completed":
        for act in suggested_actions:
            await db.agent_actions.insert_one({
                "user_id": user_id,
                "consultation_id": consultation_id,
                "action_type": act.action_type,
                "title": act.title,
                "data": act.payload,
                "status": "completed",
                "created_at": now
            })

    return AgentResponse(
        consultation_id=consultation_id,
        task_type=request.task_type,
        message=agent_message,
        thought_pipeline=thought_steps,
        missing_questions=missing_questions,
        quick_replies=quick_replies,
        stage=stage,
        red_flags_detected=red_flags,
        suggested_actions=suggested_actions,
        context_used={
            "bmi": context_data.profile_summary.get("bmi"),
            "conditions": context_data.profile_summary.get("medical_conditions"),
            "medications": context_data.profile_summary.get("current_medications"),
            "allergies": context_data.profile_summary.get("allergies"),
            "lifestyle": context_data.lifestyle_summary
        }
    )


def _smart_fallback_engine(
    request: AgentInteractRequest,
    context: AgentContextResponse,
    messages_history: list[dict]
) -> dict:
    """Deterministic, stage-aware conversation engine guaranteeing smooth multi-turn triage."""
    q = request.message.lower().strip()
    user_name = context.user_name or "User"
    bmi = context.profile_summary.get("bmi", "20.6")
    bmi_cat = context.profile_summary.get("bmi_category", "Normal weight")
    sleep = context.lifestyle_summary.get("sleep_hours", 7.5)
    stress = context.lifestyle_summary.get("stress_level", "low")
    water = context.lifestyle_summary.get("water_intake_liters", 2.0)
    exercise = context.lifestyle_summary.get("exercise_minutes_per_day", 45)

    # STAGE 5: COMPLETED
    if any(k in q for k in ["create all goals", "confirm goals", "activate goals"]):
        msg = (
            "✓ Assessment saved to your health history\n"
            "✓ 3 personalized health goals created and tracked\n\n"
            "All data is stored in your profile. You can review your active goals below or in your Health Dashboard."
        )
        return {
            "stage": "completed",
            "message": msg,
            "quick_replies": ["Ask another health question", "Review My Goals"],
            "missing_questions": [],
            "suggested_actions": [
                AgentActionItem(action_type="create_goal", title="Sleep Consistency: 7.5-8h Daily", description="Maintain restful sleep routine.", payload={"metric": "Sleep", "target": "7.5h"}),
                AgentActionItem(action_type="create_goal", title="Hydration Boost: 2.5L Water Daily", description="Increase fluid intake to reduce muscle stiffness and headache triggers.", payload={"metric": "Water", "target": "2.5L"}),
                AgentActionItem(action_type="create_goal", title="Daily 15-min Mobility & Stretching", description="Gentle shoulder, neck, and back relief exercises.", payload={"metric": "Stretching", "target": "15 min"})
            ],
            "thought_steps": [AgentThoughtStep(stage="ACT", detail="Persisted 3 active health goals and saved assessment record.")]
        }

    # STAGE 4: GOALS
    if any(k in q for k in ["create health goals", "create goals", "goals", "set goals"]):
        msg = (
            f"Based on your assessment and health metrics (BMI: {bmi}, Sleep: {sleep}h, Water: {water}L), here are 3 high-leverage personalized goals:\n\n"
            f"1. 🛌 **Sleep Consistency Target**: Aim for 7.5–8.0 hours of sleep each night to accelerate tissue repair and tension relief.\n"
            f"2. 💧 **Hydration Target**: Increase daily water intake from {water}L to 2.5L to support muscular recovery and prevent vascular headaches.\n"
            f"3. 🧘 **Mobility & Tension Relief**: Complete a 15-minute ergonomic stretch and mobility routine every evening.\n\n"
            "Would you like me to activate and track all 3 goals?"
        )
        return {
            "stage": "goals",
            "message": msg,
            "quick_replies": ["Create All Goals", "Modify Goals"],
            "missing_questions": [],
            "suggested_actions": [
                AgentActionItem(action_type="create_goal", title="Create All Goals", description="Record all 3 personalized health goals to your active tracker.", payload={"action": "create_all"})
            ],
            "thought_steps": [AgentThoughtStep(stage="ANALYZE", detail="Synthesized 3 targeted lifestyle goals based on profile telemetry.")]
        }

    # STAGE 3: GUIDANCE (Cleared Red Flags)
    if any(k in q for k in ["no, none of those", "none of those", "no symptoms", "i don't have any of those", "none"]):
        msg = (
            "Good, that helps rule out immediate red flags.\n\n"
            f"### 📋 Personalized Assessment for {user_name}:\n"
            f"- **Profile Context**: Your BMI is {bmi} ({bmi_cat}) with {exercise}m of daily activity. Average sleep is {sleep}h with {stress} stress and {water}L hydration.\n"
            "- **Clinical Pattern**: Your symptoms point toward localized muscular strain or tension without acute neurological or systemic complications.\n"
            "- **Recommended At-Home Care**: Apply alternating heat/cold compresses, stay well hydrated, and maintain good posture during workouts and desk work.\n"
            "- **When to Seek Care**: If symptoms worsen significantly or do not improve over the next 3–5 days, consult a physician.\n\n"
            "What would you like to do next?"
        )
        return {
            "stage": "guidance",
            "message": msg,
            "quick_replies": ["🎯 Create Health Goals", "📋 Save Assessment", "📊 Analyze Lifestyle Factors", "📝 Doctor Visit Summary"],
            "missing_questions": [],
            "suggested_actions": [
                AgentActionItem(action_type="create_goal", title="🎯 Create Health Goals", description="Formulate 3 tailored recovery goals.", payload={"target": "goals"}),
                AgentActionItem(action_type="health_log", title="📋 Save Assessment", description="Save to your longitudinal health record.", payload={"status": "saved"}),
                AgentActionItem(action_type="lifestyle_tweak", title="📊 Analyze Lifestyle Factors", description="Deep dive into sleep and stress habits.", payload={"category": "lifestyle"}),
                AgentActionItem(action_type="screening_alert", title="📝 Doctor Visit Summary", description="Generate a physician discussion sheet.", payload={"type": "summary"})
            ],
            "thought_steps": [AgentThoughtStep(stage="ANALYZE", detail="Cleared red-flag triage and delivered personalized guidance with 4 action options.")]
        }

    # STAGE 2: SAFETY SCREEN (User specified location, severity, or triggers)
    if any(k in q for k in ["forehead", "front of head", "around the eyes", "back of neck", "shoulders", "moderate", "severe", "mild", "5/10", "lifting weights", "almost every day", "several times"]):
        msg = (
            "Thank you. Before continuing, I need to check for symptoms that may require prompt medical attention. Are you experiencing any of the following?\n\n"
            "- Sudden, unusually severe pain or 'thunderclap' headache\n"
            "- High fever or stiff neck\n"
            "- Vision changes, slurred speech, or weakness/numbness on one side\n"
            "- Shortness of breath or chest pressure"
        )
        return {
            "stage": "safety_screen",
            "message": msg,
            "quick_replies": ["No, none of those", "Yes, I have symptoms"],
            "missing_questions": ["Any neurological signs, fever, or chest involvement?"],
            "suggested_actions": [],
            "thought_steps": [AgentThoughtStep(stage="SAFETY_CHECK", detail="Triage screen for urgent neurological, cardiovascular, and infection red flags.")]
        }

    # STAGE 1 (Sub-step 2): Duration provided -> Ask frequency
    if any(k in q for k in ["week", "weeks", "days", "day", "yesterday", "month", "today"]):
        msg = "Understood. How frequently are these symptoms occurring?"
        return {
            "stage": "intake",
            "message": msg,
            "quick_replies": ["Once a week", "2–3 times a week", "Almost every day", "Several times a day"],
            "missing_questions": ["How frequently do these symptoms occur?"],
            "suggested_actions": [],
            "thought_steps": [AgentThoughtStep(stage="PROBE", detail="Evaluating symptom frequency and episodic pattern.")]
        }

    # STAGE 1 (Initial): Start intake
    msg = (
        f"Hi {user_name}! I'm DUSY, your personalized health intelligence agent. I've reviewed your profile and logged vitals. "
        "I can help you assess the pattern.\n\n"
        "How long have you been experiencing this?"
    )
    return {
        "stage": "intake",
        "message": msg,
        "quick_replies": ["Around two weeks", "A few days", "Over a month", "Just started yesterday"],
        "missing_questions": ["How long have you had this symptom?"],
        "suggested_actions": [],
        "thought_steps": [AgentThoughtStep(stage="RETRIEVE", detail=f"Retrieved profile for {user_name}, initiating focused intake.")]
    }


async def get_user_consultations(user_id: str) -> list[AgentConsultationSummary]:
    """List recent consultations for the user."""
    db = get_database()
    cursor = db.agent_consultations.find(
        {"user_id": user_id}
    ).sort("updated_at", -1).limit(20)

    summaries = []
    async for doc in cursor:
        messages = doc.get("messages", [])
        last_preview = messages[-1]["content"][:100] + "..." if messages else "New Consultation"
        summaries.append(AgentConsultationSummary(
            id=str(doc["_id"]),
            task_type=doc.get("task_type", "symptom_assessment"),
            title=doc.get("title", "Consultation"),
            preview=last_preview,
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow()),
            message_count=len(messages)
        ))
    return summaries


async def get_consultation_details(consultation_id: str, user_id: str) -> dict:
    """Fetch complete consultation transcript and context."""
    db = get_database()
    doc = await db.agent_consultations.find_one({
        "_id": ObjectId(consultation_id),
        "user_id": user_id
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Consultation not found.")
    doc["_id"] = str(doc["_id"])
    return doc


async def execute_agent_action(request: AgentActionExecutionRequest, user_id: str) -> dict:
    """Execute and persist an action generated by the agent."""
    db = get_database()
    now = datetime.utcnow()

    # If title is Create All Goals or action_type is create_goal with multiple goals
    if "all goals" in request.title.lower():
        goals = [
            {"title": "Sleep Consistency: 7.5-8h Daily", "data": {"metric": "Sleep", "target": "7.5h"}},
            {"title": "Hydration Boost: 2.5L Water Daily", "data": {"metric": "Water", "target": "2.5L"}},
            {"title": "Daily 15-min Mobility & Stretching", "data": {"metric": "Stretching", "target": "15 min"}}
        ]
        created_ids = []
        for g in goals:
            rec = {
                "user_id": user_id,
                "consultation_id": request.consultation_id,
                "action_type": "create_goal",
                "title": g["title"],
                "data": g["data"],
                "status": "completed",
                "created_at": now
            }
            res = await db.agent_actions.insert_one(rec)
            created_ids.append(str(res.inserted_id))

        return {
            "action_id": created_ids[0],
            "status": "success",
            "message": "Successfully activated all 3 health goals in your tracker!"
        }

    action_record = {
        "user_id": user_id,
        "consultation_id": request.consultation_id,
        "action_type": request.action_type,
        "title": request.title,
        "data": request.data,
        "status": "completed",
        "created_at": now
    }
    result = await db.agent_actions.insert_one(action_record)
    return {
        "action_id": str(result.inserted_id),
        "status": "success",
        "message": f"Successfully recorded action: '{request.title}'"
    }


async def get_user_actions(user_id: str) -> list[dict]:
    """Retrieve all recorded actions and health goals for the user."""
    db = get_database()
    cursor = db.agent_actions.find({"user_id": user_id}).sort("created_at", -1).limit(50)
    actions = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc["_id"] = str(doc["_id"])
        actions.append(doc)
    return actions
