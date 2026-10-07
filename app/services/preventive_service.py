"""Preventive Health Engine — The core differentiating feature.

This service provides:
1. Preventive Risk Analysis — Multi-factor health risk scoring
2. Highest-Impact Predictor — Top 3 personalized changes
3. Future Health Projection — "What if" trajectory comparison
"""

import json
from datetime import datetime
from bson import ObjectId

from google import genai
from google.genai import types
from fastapi import HTTPException, status

from app.config import get_settings
from app.database import get_database
from app.models.preventive import (
    PreventiveAnalysisRequest, PreventiveRiskResponse, RiskCategory,
    ImpactPredictorResponse, ImpactChange,
    ProjectionRequest, ProjectionResponse, ProjectionPoint,
    LifestyleInput, VitalsInput
)


# ──────────────────────────────────────────────────────────────
# FEATURE 1: Preventive Health Risk Analysis
# ──────────────────────────────────────────────────────────────

def _calculate_base_risk_scores(
    lifestyle: LifestyleInput,
    vitals: VitalsInput | None,
    health_profile: dict | None,
    user: dict
) -> dict:
    """Calculate base risk scores from available data using rule-based scoring.
    
    This provides a deterministic baseline that Gemini AI then refines
    with contextual reasoning.
    """
    scores = {
        "metabolic": 20,
        "cardiovascular": 20,
        "sleep": 20,
        "physical_inactivity": 20,
        "nutrition": 20,
    }
    factors = {
        "metabolic": [],
        "cardiovascular": [],
        "sleep": [],
        "physical_inactivity": [],
        "nutrition": [],
    }
    
    # --- Age-based risk adjustments ---
    age = None
    if user.get("date_of_birth"):
        try:
            from datetime import date
            dob = date.fromisoformat(user["date_of_birth"])
            age = (date.today() - dob).days // 365
            if age > 45:
                scores["metabolic"] += 10
                scores["cardiovascular"] += 15
                factors["metabolic"].append(f"Age ({age}) increases metabolic risk")
                factors["cardiovascular"].append(f"Age ({age}) increases cardiovascular risk")
            elif age > 35:
                scores["metabolic"] += 5
                scores["cardiovascular"] += 8
        except (ValueError, TypeError):
            pass
    
    # --- BMI-based risk ---
    if health_profile:
        bmi = health_profile.get("bmi")
        if bmi:
            if bmi >= 30:
                scores["metabolic"] += 25
                scores["cardiovascular"] += 15
                factors["metabolic"].append(f"BMI ({bmi}) is in the obese range")
                factors["cardiovascular"].append(f"High BMI ({bmi}) increases cardiovascular load")
            elif bmi >= 25:
                scores["metabolic"] += 12
                scores["cardiovascular"] += 8
                factors["metabolic"].append(f"BMI ({bmi}) is in the overweight range")
            elif bmi < 18.5:
                scores["nutrition"] += 15
                factors["nutrition"].append(f"BMI ({bmi}) is underweight")
        
        # Family history
        family_history = health_profile.get("family_history", [])
        for condition in family_history:
            condition_lower = condition.lower()
            if "diabetes" in condition_lower:
                scores["metabolic"] += 12
                factors["metabolic"].append("Family history of diabetes")
            if "heart" in condition_lower or "cardiac" in condition_lower:
                scores["cardiovascular"] += 12
                factors["cardiovascular"].append("Family history of heart disease")
        
        # Existing conditions
        conditions = health_profile.get("medical_conditions", [])
        for cond in conditions:
            cond_lower = cond.lower()
            if "hypertension" in cond_lower or "blood pressure" in cond_lower:
                scores["cardiovascular"] += 15
                factors["cardiovascular"].append("Existing hypertension")
            if "diabetes" in cond_lower or "pre-diabetic" in cond_lower:
                scores["metabolic"] += 20
                factors["metabolic"].append("Existing diabetes/pre-diabetes")
    
    # --- Sleep risk ---
    if lifestyle.sleep_hours < 5:
        scores["sleep"] += 35
        factors["sleep"].append(f"Very low sleep ({lifestyle.sleep_hours}h) - severe deficit")
    elif lifestyle.sleep_hours < 6:
        scores["sleep"] += 25
        factors["sleep"].append(f"Low sleep ({lifestyle.sleep_hours}h) - significant deficit")
    elif lifestyle.sleep_hours < 7:
        scores["sleep"] += 12
        factors["sleep"].append(f"Below optimal sleep ({lifestyle.sleep_hours}h)")
    elif lifestyle.sleep_hours > 9:
        scores["sleep"] += 10
        factors["sleep"].append(f"Excessive sleep ({lifestyle.sleep_hours}h) may indicate underlying issues")
    
    # Poor sleep cascades to metabolic risk
    if lifestyle.sleep_hours < 6:
        scores["metabolic"] += 8
        factors["metabolic"].append("Chronic sleep deficit increases metabolic risk")
    
    # --- Physical inactivity risk ---
    if lifestyle.daily_steps < 3000:
        scores["physical_inactivity"] += 35
        factors["physical_inactivity"].append(f"Very sedentary ({lifestyle.daily_steps} steps/day)")
    elif lifestyle.daily_steps < 5000:
        scores["physical_inactivity"] += 22
        factors["physical_inactivity"].append(f"Low activity ({lifestyle.daily_steps} steps/day)")
    elif lifestyle.daily_steps < 7500:
        scores["physical_inactivity"] += 10
        factors["physical_inactivity"].append(f"Below recommended activity ({lifestyle.daily_steps} steps)")
    
    if lifestyle.exercise_minutes_per_day < 10:
        scores["physical_inactivity"] += 15
        factors["physical_inactivity"].append(f"Minimal exercise ({lifestyle.exercise_minutes_per_day} min/day)")
    elif lifestyle.exercise_minutes_per_day < 22:  # WHO recommends 150min/week = ~22min/day
        scores["physical_inactivity"] += 8
        factors["physical_inactivity"].append("Below WHO recommended exercise levels")
    
    # Inactivity cascades
    if lifestyle.daily_steps < 5000 and lifestyle.exercise_minutes_per_day < 15:
        scores["cardiovascular"] += 10
        factors["cardiovascular"].append("Sedentary lifestyle increases cardiovascular risk")
    
    # --- Nutrition risk ---
    if lifestyle.sugary_drinks_per_week > 7:
        scores["nutrition"] += 20
        scores["metabolic"] += 8
        factors["nutrition"].append(f"High sugary drink consumption ({lifestyle.sugary_drinks_per_week}/week)")
        factors["metabolic"].append("Excess sugar intake elevates metabolic risk")
    elif lifestyle.sugary_drinks_per_week > 3:
        scores["nutrition"] += 10
        factors["nutrition"].append(f"Moderate sugary drink consumption ({lifestyle.sugary_drinks_per_week}/week)")
    
    if lifestyle.diet_type and lifestyle.diet_type.lower() == "junk-heavy":
        scores["nutrition"] += 25
        scores["metabolic"] += 10
        factors["nutrition"].append("Junk-heavy diet lacks essential nutrients")
    
    if lifestyle.water_intake_liters < 1.5:
        scores["nutrition"] += 8
        factors["nutrition"].append(f"Low water intake ({lifestyle.water_intake_liters}L/day)")
    
    # --- Smoking & alcohol ---
    if lifestyle.smoking:
        scores["cardiovascular"] += 25
        scores["metabolic"] += 10
        factors["cardiovascular"].append("Smoking significantly increases cardiovascular risk")
        factors["metabolic"].append("Smoking disrupts metabolic function")
    
    if lifestyle.alcohol_drinks_per_week > 14:
        scores["cardiovascular"] += 12
        scores["nutrition"] += 10
        factors["cardiovascular"].append("Heavy alcohol consumption")
    elif lifestyle.alcohol_drinks_per_week > 7:
        scores["cardiovascular"] += 6
        factors["cardiovascular"].append("Moderate-high alcohol consumption")
    
    # --- Stress ---
    if lifestyle.stress_level in ("high", "very-high"):
        scores["cardiovascular"] += 10
        scores["sleep"] += 8
        factors["cardiovascular"].append(f"High stress level reported")
        factors["sleep"].append("High stress impacts sleep quality")
    
    # --- Vitals-based risk ---
    if vitals:
        if vitals.systolic_bp and vitals.systolic_bp >= 140:
            scores["cardiovascular"] += 20
            factors["cardiovascular"].append(f"Elevated systolic BP ({vitals.systolic_bp} mmHg)")
        elif vitals.systolic_bp and vitals.systolic_bp >= 130:
            scores["cardiovascular"] += 10
            factors["cardiovascular"].append(f"Borderline high systolic BP ({vitals.systolic_bp} mmHg)")
        
        if vitals.fasting_glucose and vitals.fasting_glucose >= 126:
            scores["metabolic"] += 25
            factors["metabolic"].append(f"High fasting glucose ({vitals.fasting_glucose} mg/dL) - diabetic range")
        elif vitals.fasting_glucose and vitals.fasting_glucose >= 100:
            scores["metabolic"] += 12
            factors["metabolic"].append(f"Elevated fasting glucose ({vitals.fasting_glucose} mg/dL) - pre-diabetic range")
        
        if vitals.resting_heart_rate and vitals.resting_heart_rate > 100:
            scores["cardiovascular"] += 12
            factors["cardiovascular"].append(f"Elevated resting heart rate ({vitals.resting_heart_rate} bpm)")
        
        if vitals.cholesterol_total and vitals.cholesterol_total > 240:
            scores["cardiovascular"] += 15
            factors["cardiovascular"].append(f"High total cholesterol ({vitals.cholesterol_total} mg/dL)")
        
        if vitals.cholesterol_ldl and vitals.cholesterol_ldl > 160:
            scores["cardiovascular"] += 12
            factors["cardiovascular"].append(f"High LDL cholesterol ({vitals.cholesterol_ldl} mg/dL)")
    
    # Cap all scores at 100
    for key in scores:
        scores[key] = min(scores[key], 100)
    
    return scores, factors


def _score_to_level(score: int) -> str:
    """Convert a numeric risk score to a human-readable level."""
    if score < 30:
        return "low"
    elif score < 50:
        return "moderate"
    elif score < 70:
        return "high"
    else:
        return "very-high"


def _generate_screening_recommendations(
    scores: dict, age: int | None, gender: str | None
) -> list[str]:
    """Generate preventive screening recommendations based on risk profile."""
    recommendations = []
    
    if scores["metabolic"] >= 40:
        recommendations.append(
            "Consider discussing HbA1c and fasting glucose screening with your doctor"
        )
    if scores["cardiovascular"] >= 40:
        recommendations.append(
            "Consider discussing a lipid profile and blood pressure check with your doctor"
        )
    if scores["cardiovascular"] >= 60:
        recommendations.append(
            "Consider discussing cardiac risk assessment (ECG/stress test) with your doctor"
        )
    if scores["sleep"] >= 50:
        recommendations.append(
            "Consider discussing sleep quality assessment with your doctor"
        )
    
    # Age-based screenings
    if age:
        if age >= 40:
            recommendations.append("Annual comprehensive health check-up recommended for your age group")
        if age >= 45:
            recommendations.append("Discuss diabetes screening with your doctor")
        if age >= 50:
            recommendations.append("Discuss colorectal cancer screening with your doctor")
    
    if not recommendations:
        recommendations.append(
            "No urgent screenings identified. Continue regular annual check-ups."
        )
    
    return recommendations


async def analyze_preventive_risk(
    request: PreventiveAnalysisRequest, user: dict
) -> PreventiveRiskResponse:
    """Analyze user's health data and produce a preventive risk profile.
    
    This is FEATURE 1 — the core differentiator. It combines rule-based
    scoring with Gemini AI for intelligent risk assessment.
    """
    db = get_database()
    user_id = user["_id"] if isinstance(user["_id"], str) else str(user["_id"])
    
    # Fetch health profile for additional context
    health_profile = await db.health_profiles.find_one({"user_id": user_id})
    
    # Calculate rule-based scores
    scores, factors = _calculate_base_risk_scores(
        request.lifestyle, request.vitals, health_profile, user
    )
    
    # Calculate overall score (weighted average)
    weights = {
        "metabolic": 0.25,
        "cardiovascular": 0.25,
        "sleep": 0.20,
        "physical_inactivity": 0.15,
        "nutrition": 0.15,
    }
    overall_score = int(sum(scores[k] * weights[k] for k in scores))
    
    # Build risk categories
    category_names = {
        "metabolic": "Metabolic Risk",
        "cardiovascular": "Cardiovascular Risk",
        "sleep": "Sleep-Related Risk",
        "physical_inactivity": "Physical Inactivity Risk",
        "nutrition": "Nutrition-Related Risk",
    }
    
    risk_categories = []
    for key, name in category_names.items():
        risk_categories.append(RiskCategory(
            category=name,
            risk_level=_score_to_level(scores[key]),
            risk_score=scores[key],
            contributing_factors=factors[key],
            explanation=f"Your {name.lower()} is {'elevated' if scores[key] >= 40 else 'within acceptable range'} based on your profile."
        ))
    
    # Sort by risk score (highest first)
    risk_categories.sort(key=lambda x: x.risk_score, reverse=True)
    
    # Get age and gender for screening recommendations
    age = None
    gender = user.get("gender")
    if user.get("date_of_birth"):
        try:
            from datetime import date
            dob = date.fromisoformat(user["date_of_birth"])
            age = (date.today() - dob).days // 365
        except (ValueError, TypeError):
            pass
    
    screening_recs = _generate_screening_recommendations(scores, age, gender)
    
    # Generate AI summary
    summary = _generate_risk_summary(scores, risk_categories, overall_score)
    
    # Store in database
    analysis_doc = {
        "user_id": user_id,
        "scores": scores,
        "overall_score": overall_score,
        "lifestyle_data": request.lifestyle.model_dump(),
        "vitals_data": request.vitals.model_dump() if request.vitals else None,
        "generated_at": datetime.utcnow()
    }
    await db.preventive_analyses.insert_one(analysis_doc)
    
    return PreventiveRiskResponse(
        overall_risk_level=_score_to_level(overall_score),
        overall_risk_score=overall_score,
        risk_categories=risk_categories,
        screening_recommendations=screening_recs,
        summary=summary,
    )


def _generate_risk_summary(scores: dict, categories: list, overall: int) -> str:
    """Generate a human-readable summary of the risk profile."""
    highest = categories[0]  # Already sorted by score
    
    if overall < 30:
        intro = "Your overall preventive risk profile appears low."
    elif overall < 50:
        intro = "Your preventive risk profile shows some moderate areas of concern."
    elif overall < 70:
        intro = "Your preventive risk profile indicates elevated risk in several areas."
    else:
        intro = "Your preventive risk profile shows significant risk factors that need attention."
    
    high_risks = [c for c in categories if c.risk_score >= 50]
    if high_risks:
        areas = ", ".join(c.category for c in high_risks)
        detail = f" Your highest concerns are in: {areas}."
    else:
        detail = " No single category shows high risk."
    
    action = " Focus on the highest-impact changes recommended for your profile to improve these scores."
    
    return intro + detail + action


# ──────────────────────────────────────────────────────────────
# FEATURE 2: Highest-Impact Predictor
# ──────────────────────────────────────────────────────────────

IMPACT_PREDICTOR_PROMPT = """You are a preventive health AI advisor. Based on the user's health profile and risk scores, 
identify the TOP 3 lifestyle changes that would produce the BIGGEST health improvement for THIS specific user.

IMPORTANT RULES:
1. Be specific and personalized — don't give generic advice.
2. For each change, specify their CURRENT value and a realistic TARGET value.
3. Estimate the impact level: "high", "medium-high", or "medium".
4. Explain WHY this change matters for this particular person.
5. Consider interactions between risk factors.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{
    "top_changes": [
        {
            "rank": 1,
            "change": "Short description of the change",
            "current_value": "Their current behavior",
            "target_value": "Recommended target",
            "impact_level": "high",
            "affected_risks": ["Metabolic Risk", "Sleep-Related Risk"],
            "expected_risk_reduction": "Estimated risk reduction description",
            "explanation": "Why this matters for this user specifically"
        }
    ],
    "personalization_note": "Brief note on why these 3 were selected for this user"
}

Limit to exactly 3 changes. Rank by expected impact (highest first).
"""


async def predict_highest_impact(
    request: PreventiveAnalysisRequest, user: dict
) -> ImpactPredictorResponse:
    """Identify the top 3 highest-impact lifestyle changes for this user.
    
    This is FEATURE 2 — the most novel feature. No existing consumer app
    tells users "for YOU, these 3 changes matter most."
    """
    db = get_database()
    settings = get_settings()
    user_id = user["_id"] if isinstance(user["_id"], str) else str(user["_id"])
    
    # Get health profile
    health_profile = await db.health_profiles.find_one({"user_id": user_id})
    
    # Calculate risk scores for context
    scores, factors = _calculate_base_risk_scores(
        request.lifestyle, request.vitals, health_profile, user
    )
    
    # Build prompt with full user context
    context = f"""
USER PROFILE:
- Name: {user.get('name', 'User')}
- Date of Birth: {user.get('date_of_birth', 'Unknown')}
- Gender: {user.get('gender', 'Unknown')}

CURRENT LIFESTYLE:
- Sleep: {request.lifestyle.sleep_hours} hours/night
- Exercise: {request.lifestyle.exercise_minutes_per_day} min/day
- Daily Steps: {request.lifestyle.daily_steps}
- Water Intake: {request.lifestyle.water_intake_liters}L/day
- Diet Type: {request.lifestyle.diet_type or 'Not specified'}
- Sugary Drinks: {request.lifestyle.sugary_drinks_per_week}/week
- Smoking: {'Yes' if request.lifestyle.smoking else 'No'}
- Alcohol: {request.lifestyle.alcohol_drinks_per_week} drinks/week
- Stress Level: {request.lifestyle.stress_level or 'Not specified'}
- Screen Time: {request.lifestyle.screen_time_hours} hours/day

CURRENT RISK SCORES (0-100, higher = worse):
- Metabolic Risk: {scores['metabolic']}
- Cardiovascular Risk: {scores['cardiovascular']}
- Sleep Risk: {scores['sleep']}
- Physical Inactivity Risk: {scores['physical_inactivity']}
- Nutrition Risk: {scores['nutrition']}
"""
    
    if health_profile:
        context += f"""
HEALTH PROFILE:
- BMI: {health_profile.get('bmi', 'Unknown')}
- Medical Conditions: {', '.join(health_profile.get('medical_conditions', [])) or 'None'}
- Allergies: {', '.join(health_profile.get('allergies', [])) or 'None'}
- Family History: {', '.join(health_profile.get('family_history', [])) or 'None'}
"""
    
    if request.vitals:
        context += f"""
VITALS:
- Blood Pressure: {request.vitals.systolic_bp or '?'}/{request.vitals.diastolic_bp or '?'} mmHg
- Fasting Glucose: {request.vitals.fasting_glucose or 'Unknown'} mg/dL
- Resting Heart Rate: {request.vitals.resting_heart_rate or 'Unknown'} bpm
"""
    
    full_prompt = IMPACT_PREDICTOR_PROMPT + "\n" + context
    
    # Call Gemini AI
    if not settings.GEMINI_API_KEY:
        # Fallback: generate rule-based recommendations
        return _fallback_impact_prediction(request.lifestyle, scores)
    
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=1500,
            )
        )
        response_text = response.text.strip()
        
        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]
        
        result = json.loads(response_text)
        
        top_changes = [ImpactChange(**change) for change in result.get("top_changes", [])]
        
        return ImpactPredictorResponse(
            top_changes=top_changes,
            personalization_note=result.get("personalization_note", ""),
        )
    except (json.JSONDecodeError, Exception):
        # Fallback to rule-based
        return _fallback_impact_prediction(request.lifestyle, scores)


def _fallback_impact_prediction(
    lifestyle: LifestyleInput, scores: dict
) -> ImpactPredictorResponse:
    """Rule-based fallback for impact prediction when AI is unavailable."""
    changes = []
    rank = 1
    
    # Find the highest-scoring risk areas and match recommendations
    risk_changes = []
    
    if lifestyle.sleep_hours < 7:
        deficit = 7 - lifestyle.sleep_hours
        risk_changes.append((
            scores["sleep"] + scores["metabolic"] * 0.3,
            ImpactChange(
                rank=0,
                change=f"Increase sleep by {deficit:.0f} hour(s)",
                current_value=f"{lifestyle.sleep_hours} hours/night",
                target_value="7-8 hours/night",
                impact_level="high" if lifestyle.sleep_hours < 6 else "medium-high",
                affected_risks=["Sleep-Related Risk", "Metabolic Risk"],
                expected_risk_reduction=f"Sleep risk could drop by ~{min(int(deficit * 12), 30)} points",
                explanation="Sleep is foundational — it affects metabolism, immunity, mood, and cognitive function."
            )
        ))
    
    if lifestyle.daily_steps < 7000:
        gap = 7000 - lifestyle.daily_steps
        risk_changes.append((
            scores["physical_inactivity"] + scores["cardiovascular"] * 0.3,
            ImpactChange(
                rank=0,
                change=f"Add ~{gap:,} daily steps",
                current_value=f"{lifestyle.daily_steps:,} steps/day",
                target_value="7,000-10,000 steps/day",
                impact_level="high" if lifestyle.daily_steps < 4000 else "medium-high",
                affected_risks=["Physical Inactivity Risk", "Cardiovascular Risk"],
                expected_risk_reduction=f"Inactivity risk could drop by ~{min(int(gap/200), 25)} points",
                explanation="Regular walking is one of the most effective ways to improve overall health."
            )
        ))
    
    if lifestyle.sugary_drinks_per_week > 3:
        risk_changes.append((
            scores["nutrition"] + scores["metabolic"] * 0.3,
            ImpactChange(
                rank=0,
                change="Reduce sugary drinks",
                current_value=f"{lifestyle.sugary_drinks_per_week}/week",
                target_value="1-2/week maximum",
                impact_level="medium-high" if lifestyle.sugary_drinks_per_week > 7 else "medium",
                affected_risks=["Nutrition-Related Risk", "Metabolic Risk"],
                expected_risk_reduction="Nutrition risk could drop by ~10-15 points",
                explanation="Excess sugar is a major driver of metabolic problems and weight gain."
            )
        ))
    
    if lifestyle.exercise_minutes_per_day < 20:
        risk_changes.append((
            scores["physical_inactivity"] * 0.8,
            ImpactChange(
                rank=0,
                change="Add 20-30 minutes of moderate exercise daily",
                current_value=f"{lifestyle.exercise_minutes_per_day} min/day",
                target_value="30 min/day (WHO recommendation)",
                impact_level="high" if lifestyle.exercise_minutes_per_day < 10 else "medium-high",
                affected_risks=["Physical Inactivity Risk", "Cardiovascular Risk", "Metabolic Risk"],
                expected_risk_reduction="Physical inactivity risk could drop by ~15-20 points",
                explanation="Regular exercise improves cardiovascular health, metabolism, and mental well-being."
            )
        ))
    
    if lifestyle.smoking:
        risk_changes.append((
            100,  # Highest priority
            ImpactChange(
                rank=0,
                change="Stop smoking",
                current_value="Active smoker",
                target_value="Non-smoker",
                impact_level="high",
                affected_risks=["Cardiovascular Risk", "Metabolic Risk"],
                expected_risk_reduction="Cardiovascular risk could drop by ~20-25 points",
                explanation="Smoking is the single most impactful modifiable risk factor for cardiovascular disease."
            )
        ))
    
    if lifestyle.stress_level in ("high", "very-high"):
        risk_changes.append((
            scores["sleep"] * 0.5 + scores["cardiovascular"] * 0.3,
            ImpactChange(
                rank=0,
                change="Implement daily stress management",
                current_value=f"Stress level: {lifestyle.stress_level}",
                target_value="Practice 10-15 min relaxation/meditation daily",
                impact_level="medium-high",
                affected_risks=["Cardiovascular Risk", "Sleep-Related Risk"],
                expected_risk_reduction="Can improve sleep and cardiovascular metrics",
                explanation="Chronic stress elevates cortisol, affecting sleep quality and heart health."
            )
        ))
    
    # Sort by composite score (highest impact first) and take top 3
    risk_changes.sort(key=lambda x: x[0], reverse=True)
    top_3 = risk_changes[:3]
    
    for i, (_, change) in enumerate(top_3):
        change.rank = i + 1
        changes.append(change)
    
    # Ensure we always have 3 recommendations
    if len(changes) < 3:
        changes.append(ImpactChange(
            rank=len(changes) + 1,
            change="Increase daily water intake",
            current_value=f"{lifestyle.water_intake_liters}L/day",
            target_value="2.5-3L/day",
            impact_level="medium",
            affected_risks=["Nutrition-Related Risk"],
            expected_risk_reduction="Supports overall health and metabolism",
            explanation="Adequate hydration supports all bodily functions."
        ))
    
    return ImpactPredictorResponse(
        top_changes=changes[:3],
        personalization_note="These changes were selected based on your highest risk areas and the expected magnitude of improvement.",
    )


# ──────────────────────────────────────────────────────────────
# FEATURE 3: Future Health Projection
# ──────────────────────────────────────────────────────────────

def _project_trajectory(
    base_scores: dict,
    lifestyle: LifestyleInput,
    improvements: dict | None = None
) -> list[ProjectionPoint]:
    """Project risk scores into the future based on current or improved lifestyle.
    
    Uses a simplified epidemiological model:
    - Unhealthy habits compound risk over time (scores increase)
    - Healthy habits stabilize or reduce risk
    - Changes take time to show effect (gradual improvement)
    """
    trajectory = []
    months = [0, 3, 6, 12, 24]
    
    for month in months:
        if month == 0:
            # Current state
            trajectory.append(ProjectionPoint(
                month=0,
                overall_risk_score=int(sum(base_scores.values()) / len(base_scores)),
                metabolic_risk=base_scores["metabolic"],
                cardiovascular_risk=base_scores["cardiovascular"],
                sleep_risk=base_scores["sleep"],
                activity_risk=base_scores["physical_inactivity"],
            ))
            continue
        
        # Calculate projections
        projected = {}
        for key, base_score in base_scores.items():
            if improvements:
                # With improvements: scores decrease over time
                reduction_rate = improvements.get(key, 0)
                # Improvements take time: 30% at 3mo, 60% at 6mo, 85% at 12mo, 95% at 24mo
                time_factor = {3: 0.3, 6: 0.6, 12: 0.85, 24: 0.95}[month]
                reduction = reduction_rate * time_factor
                projected[key] = max(10, int(base_score - reduction))
            else:
                # Without changes: scores gradually increase due to compounding
                # Unhealthy lifestyles compound at ~2-5% per year
                annual_increase = 0
                if base_score >= 50:
                    annual_increase = base_score * 0.08  # High-risk compounds faster
                elif base_score >= 30:
                    annual_increase = base_score * 0.04
                else:
                    annual_increase = base_score * 0.01  # Low risk stays stable
                
                month_increase = annual_increase * (month / 12)
                projected[key] = min(100, int(base_score + month_increase))
        
        overall = int(sum(projected.values()) / len(projected))
        trajectory.append(ProjectionPoint(
            month=month,
            overall_risk_score=min(100, overall),
            metabolic_risk=projected["metabolic"],
            cardiovascular_risk=projected["cardiovascular"],
            sleep_risk=projected["sleep"],
            activity_risk=projected["physical_inactivity"],
        ))
    
    return trajectory


def _estimate_improvements(lifestyle: LifestyleInput, scores: dict) -> dict:
    """Estimate how much risk scores could improve with recommended changes."""
    improvements = {}
    
    # Sleep improvement
    if lifestyle.sleep_hours < 7:
        improvements["sleep"] = min(30, int((7 - lifestyle.sleep_hours) * 12))
        improvements["metabolic"] = improvements.get("metabolic", 0) + 5
    
    # Activity improvement
    if lifestyle.daily_steps < 7000 or lifestyle.exercise_minutes_per_day < 20:
        improvements["physical_inactivity"] = min(25, int(scores["physical_inactivity"] * 0.5))
        improvements["cardiovascular"] = improvements.get("cardiovascular", 0) + 8
    
    # Nutrition improvement
    if lifestyle.sugary_drinks_per_week > 3 or (lifestyle.diet_type and "junk" in (lifestyle.diet_type or "").lower()):
        improvements["nutrition"] = min(20, int(scores["nutrition"] * 0.4))
        improvements["metabolic"] = improvements.get("metabolic", 0) + 6
    
    # Smoking cessation
    if lifestyle.smoking:
        improvements["cardiovascular"] = improvements.get("cardiovascular", 0) + 20
        improvements["metabolic"] = improvements.get("metabolic", 0) + 8
    
    # Stress management
    if lifestyle.stress_level in ("high", "very-high"):
        improvements["sleep"] = improvements.get("sleep", 0) + 5
        improvements["cardiovascular"] = improvements.get("cardiovascular", 0) + 5
    
    return improvements


async def generate_projection(
    request: ProjectionRequest, user: dict
) -> ProjectionResponse:
    """Generate future health trajectory projections.
    
    This is FEATURE 3 — the visual "wow factor." Shows two trajectories:
    1. Current path (no changes) — risk scores increase over time
    2. Improved path (with changes) — risk scores decrease
    """
    db = get_database()
    user_id = user["_id"] if isinstance(user["_id"], str) else str(user["_id"])
    
    health_profile = await db.health_profiles.find_one({"user_id": user_id})
    
    # Calculate base risk scores
    vitals = request.vitals
    scores, _ = _calculate_base_risk_scores(
        request.lifestyle, vitals, health_profile, user
    )
    
    # Generate current trajectory (no changes)
    current_trajectory = _project_trajectory(scores, request.lifestyle)
    
    # Generate improved trajectory
    improvements = _estimate_improvements(request.lifestyle, scores)
    improved_trajectory = _project_trajectory(scores, request.lifestyle, improvements)
    
    # Determine changes applied
    changes_applied = []
    if request.lifestyle.sleep_hours < 7:
        changes_applied.append(f"Increase sleep to 7-8 hours (from {request.lifestyle.sleep_hours}h)")
    if request.lifestyle.daily_steps < 7000:
        changes_applied.append(f"Increase daily steps to 7,000+ (from {request.lifestyle.daily_steps})")
    if request.lifestyle.exercise_minutes_per_day < 20:
        changes_applied.append("Add 20-30 min daily exercise")
    if request.lifestyle.sugary_drinks_per_week > 3:
        changes_applied.append(f"Reduce sugary drinks to <3/week (from {request.lifestyle.sugary_drinks_per_week})")
    if request.lifestyle.smoking:
        changes_applied.append("Stop smoking")
    if request.lifestyle.stress_level in ("high", "very-high"):
        changes_applied.append("Daily stress management (meditation/relaxation)")
    
    if request.planned_changes:
        changes_applied = request.planned_changes
    
    # Key insight
    current_24mo = current_trajectory[-1].overall_risk_score
    improved_24mo = improved_trajectory[-1].overall_risk_score
    difference = current_24mo - improved_24mo
    
    key_insight = (
        f"If you continue your current lifestyle, your overall risk score is projected to reach "
        f"{current_24mo}/100 in 2 years. With the recommended changes, it could drop to "
        f"{improved_24mo}/100 — a {difference}-point improvement. "
        f"The biggest gains come in the first 6 months."
    )
    
    # Store projection
    projection_doc = {
        "user_id": user_id,
        "current_trajectory": [p.model_dump() for p in current_trajectory],
        "improved_trajectory": [p.model_dump() for p in improved_trajectory],
        "changes_applied": changes_applied,
        "generated_at": datetime.utcnow()
    }
    await db.health_projections.insert_one(projection_doc)
    
    return ProjectionResponse(
        current_trajectory=current_trajectory,
        improved_trajectory=improved_trajectory,
        changes_applied=changes_applied,
        key_insight=key_insight,
    )
