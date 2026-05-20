import random

# Dictionaries of humorous social captions mapped by dominant emotion
CAPTION_REGISTRY = {
    "HAPPY": [
        "Deploying confidence...",
        "Compiling happiness...",
        "AWS credits detected",
        "It compiles on the first try!",
        "Production-ready smile",
        "Salary expectations matching code quality",
    ],
    "CALM": [
        "Zen Mode: Active",
        "Thread.sleep(8000) in progress",
        "No merge conflicts in sight",
        "Running on steady caffeine levels",
        "Calm before the massive git push",
        "All tests passing silently",
    ],
    "SURPRISED": [
        "Syntax error in production?!",
        "Unexpected status code: 200 OK",
        "Did I just push to main?",
        "When the bug fixes itself",
        "Wait, we had a database backup?!",
    ],
    "SAD": [
        "Crying in clean code",
        "404 Smile Not Found",
        "Memory leak in dopamine levels",
        "Semicolon missing at line 42",
        "Need a reboot...",
    ],
    "ANGRY": [
        "Who committed this without tests?",
        "Refactoring code written by past me",
        "Merge conflict survival meeting",
        "Angry compiler noises",
        "Tab vs Space debate intensifies",
    ],
    "CONFUSED": [
        "It works on my machine...",
        "Is it a DNS issue again?",
        "What does this error message even mean?",
        "Where is the closing bracket?",
        "Who touched the config file?",
    ],
    "FEAR": [
        "Deploying on a Friday afternoon",
        "Database drop table preview...",
        "Senior developer approaching cursor",
        "git push --force deployed!",
    ],
    "fallback": [
        "Powered by caffeine and dreams",
        "Running on deadlines",
        "Compiling local environment...",
        "AI model high confidence vibes",
    ]
}

def get_caption(face: dict) -> str:
    """
    Analyzes dominant emotion in the face detail data and returns a humorous,
    social-media-style dynamic caption.
    """
    emotions = face.get("Emotions", [])
    if not emotions:
        return random.choice(CAPTION_REGISTRY["fallback"])
        
    # Get top dominant emotion
    top_emotion = max(emotions, key=lambda e: e.get("Confidence", 0))
    emotion_type = top_emotion.get("Type", "HAPPY")
    
    pool = CAPTION_REGISTRY.get(emotion_type, CAPTION_REGISTRY["fallback"])
    return random.choice(pool)
