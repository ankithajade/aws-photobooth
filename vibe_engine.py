import random

GROUP_VIBE_REGISTRY = [
    "Founders Loading...",
    "Chaos Coordinators",
    "Frontend vs Backend Squad",
    "The Debugging Board",
    "Group Project Survivors",
    "2AM Brainstorm Squad",
    "StackOverflow Copy-Pasters",
    "Merged Branch Committee",
    "Caffeine Processing unit",
]

def get_vibes(face: dict) -> dict:
    """
    Computes a set of gaming-style vibe/aura scores influenced by dominant emotion.
    """
    emotions = face.get("Emotions", [])
    top_emotion_type = "HAPPY"
    confidence = 80
    
    if emotions:
        top_emotion = max(emotions, key=lambda e: e.get("Confidence", 0))
        top_emotion_type = top_emotion.get("Type", "HAPPY")
        confidence = top_emotion.get("Confidence", 80)
        
    vibes = {}
    
    # 1. Aura Level (Influenced heavily by Happy, Calm, or Sunglasses)
    sunglasses = face.get("Sunglasses", {}).get("Value", False)
    if sunglasses:
        vibes["Aura Level"] = f"{int(random.randint(95, 100))}%"
    elif top_emotion_type in ["HAPPY", "CALM"]:
        val = int(stretching_map(confidence, 50, 100, 75, 98))
        vibes["Aura Level"] = f"{val}%"
    else:
        vibes["Aura Level"] = f"{int(random.randint(40, 75))}%"
        
    # 2. Chaos Energy (Influenced heavily by Surprise, Anger, Sadness, or Pose tilt)
    pose = face.get("Pose", {})
    tilt = abs(pose.get("Yaw", 0)) + abs(pose.get("Roll", 0))
    if top_emotion_type in ["ANGRY", "SURPRISED", "CONFUSED"] or tilt > 20:
        val = int(random.randint(75, 99))
        vibes["Chaos Energy"] = f"{val}%"
    else:
        vibes["Chaos Energy"] = f"{int(random.randint(10, 45))}%"
        
    # 3. Hackathon Power (Fun metrics)
    if top_emotion_type in ["HAPPY", "CALM"] and face.get("Smile", {}).get("Value", False):
        vibes["Hackathon Power"] = "MAX"
    else:
        vibes["Hackathon Power"] = f"{int(random.randint(70, 95))}%"
        
    # 4. Sleep Level (Slightly randomized, usually low for devs!)
    if top_emotion_type in ["SAD", "ANGRY", "CONFUSED"]:
        vibes["Sleep Level"] = "CRITICAL"
    else:
        vibes["Sleep Level"] = f"{int(random.randint(15, 45))}%"
        
    # 5. Confidence Meter (Mapped directly to dominant emotion confidence)
    vibes["Confidence Meter"] = f"{int(confidence)}%"
    
    return vibes

def get_group_vibe(faces: list) -> str:
    """
    Returns a unified team chemistry tag string if 2+ faces are present.
    """
    if len(faces) < 2:
        return ""
    return random.choice(GROUP_VIBE_REGISTRY)

def stretching_map(val, in_min, in_max, out_min, out_max):
    """Linearly maps a value from one range to another."""
    return out_min + (float(val - in_min) / float(in_max - in_min) * (out_max - out_min))
