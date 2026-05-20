import random

# Dictionaries of personas grouped by dominant facial signals
PERSONALITY_REGISTRY = {
    "glasses_smile": [
        "Debugger Supreme",
        "UI/UX Perfectionist",
        "Stack Overflow Contributor",
        "Clean Code Advocate",
    ],
    "glasses_nosmile": [
        "Cybersecurity Specialist",
        "Compiler Champion",
        "Algorithm Architect",
        "Certified Overthinker",
    ],
    "sunglasses": [
        "Startup CEO Energy",
        "Venture Capital Magnet",
        "Crypto Evangelist",
        "Metaverse Explorer",
    ],
    "beard": [
        "Future AWS Architect",
        "Open Source Maintainer",
        "Database Whisperer",
        "Senior Dev Aura",
    ],
    "smile_happy": [
        "Main Character Energy",
        "Production-Ready Coder",
        "10x Developer",
        "Cloud Ninja",
    ],
    "low_smile": [
        "Sleep-Deprived Coder",
        "Git Conflict Resolver",
        "Refactoring Maverick",
        "Running on Deadlines",
    ],
    "fallback": [
        "Future Tech Leader",
        "Hackathon Pioneer",
        "Byte Wizard",
        "API Architect",
    ]
}

def get_personality(face: dict) -> str:
    """
    Analyzes Rekognition face detail data and returns a humorous, tech-themed
    personality persona. Uses randomization for fresh results.
    """
    # Safe extractions
    smile_val = face.get("Smile", {}).get("Value", False)
    glasses = face.get("Eyeglasses", {}).get("Value", False)
    sunglasses = face.get("Sunglasses", {}).get("Value", False)
    beard = face.get("Beard", {}).get("Value", False)
    
    # Classify facial signal state
    if sunglasses:
        pool = PERSONALITY_REGISTRY["sunglasses"]
    elif glasses:
        if smile_val:
            pool = PERSONALITY_REGISTRY["glasses_smile"]
        else:
            pool = PERSONALITY_REGISTRY["glasses_nosmile"]
    elif beard:
        pool = PERSONALITY_REGISTRY["beard"]
    elif smile_val:
        pool = PERSONALITY_REGISTRY["smile_happy"]
    else:
        pool = PERSONALITY_REGISTRY["low_smile"]
        
    if not pool:
        pool = PERSONALITY_REGISTRY["fallback"]
        
    return random.choice(pool)

def get_badges(face: dict) -> list:
    """
    Analyzes accessory and facial states to generate small, fun badge chips.
    """
    badges = []
    
    # 1. Sunglasses
    if face.get("Sunglasses", {}).get("Value", False):
        badges.append("🕶️ Hacker Mode")
    elif face.get("Eyeglasses", {}).get("Value", False):
        badges.append("🤓 +10 Intelligence")
        
    # 2. Beard
    if face.get("Beard", {}).get("Value", False):
        badges.append("🧔 Elder Dev")
        
    # 3. Smile
    if face.get("Smile", {}).get("Value", False):
        badges.append("✨ Positive Energy")
    else:
        badges.append("☕ Needs Coffee")
        
    # 4. Pose
    pose = face.get("Pose", {})
    yaw = abs(pose.get("Yaw", 0))
    pitch = abs(pose.get("Pitch", 0))
    if yaw > 15 or pitch > 15:
        badges.append("🌀 Perspective Shift")
        
    return badges
