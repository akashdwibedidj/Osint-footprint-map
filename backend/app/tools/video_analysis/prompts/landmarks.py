"""
Landmark prompts for CLIP zero-shot recognition, with state/country
metadata attached. CLIP only ever matches the visual concept named in
`prompt` (a specific structure/monument) - it does NOT recognize states
or cities directly, since those are too visually diverse for one
coherent "look." The state/country fields are just a free lookup: once
CLIP identifies which landmark matched, we already know what state/
country it's in - no extra model call, no extra visual matching.

Add new entries any time - geolocation.py just imports KNOWN_LANDMARKS,
no other code changes needed.

Writing a good entry:
- "prompt": name the specific structure, not the general area.
  "the Charminar" not "Hyderabad." "Mysore Palace" not "Karnataka."
  Add a short qualifier if the name is ambiguous / shared globally.
  Keep it a natural photo-caption phrase - CLIP was trained on real
  captions, so "a photo of the Red Fort, Delhi" matches better than a
  bare keyword string.
- "state": the state/province, or None if not applicable (e.g. a
  landmark in a country with no relevant state subdivision, or a
  landmark spanning/ambiguous between regions).
- "country": always fill this in.
"""

KNOWN_LANDMARKS = [
    # Global
    {"prompt": "the Eiffel Tower", "state": None, "country": "France"},
    {"prompt": "Big Ben", "state": None, "country": "United Kingdom"},
    {"prompt": "the Statue of Liberty", "state": "New York", "country": "United States"},
    {"prompt": "the Colosseum", "state": None, "country": "Italy"},
    {"prompt": "the Great Wall of China", "state": None, "country": "China"},
    {"prompt": "the Sydney Opera House", "state": "New South Wales", "country": "Australia"},
    {"prompt": "the Golden Gate Bridge", "state": "California", "country": "United States"},
    {"prompt": "Machu Picchu", "state": None, "country": "Peru"},
    {"prompt": "the Pyramids of Giza", "state": None, "country": "Egypt"},
    {"prompt": "Christ the Redeemer statue", "state": "Rio de Janeiro", "country": "Brazil"},
    {"prompt": "the Leaning Tower of Pisa", "state": None, "country": "Italy"},
    {"prompt": "Times Square", "state": "New York", "country": "United States"},
    {"prompt": "the Burj Khalifa", "state": "Dubai", "country": "United Arab Emirates"},
    {"prompt": "the Sagrada Familia", "state": None, "country": "Spain"},
    {"prompt": "Mount Fuji", "state": None, "country": "Japan"},
    {"prompt": "Stonehenge", "state": None, "country": "United Kingdom"},
    {"prompt": "the Brandenburg Gate", "state": None, "country": "Germany"},
    {"prompt": "Notre-Dame Cathedral", "state": None, "country": "France"},
    {"prompt": "the Louvre Museum", "state": None, "country": "France"},

    # India
    {"prompt": "the Taj Mahal", "state": "Uttar Pradesh", "country": "India"},
    {"prompt": "India Gate, Delhi", "state": "Delhi", "country": "India"},
    {"prompt": "the Gateway of India, Mumbai", "state": "Maharashtra", "country": "India"},
    {"prompt": "the Golden Temple, Amritsar", "state": "Punjab", "country": "India"},
    {"prompt": "Hawa Mahal, Jaipur", "state": "Rajasthan", "country": "India"},
    {"prompt": "the Charminar, Hyderabad", "state": "Telangana", "country": "India"},
    {"prompt": "Qutub Minar, Delhi", "state": "Delhi", "country": "India"},
    {"prompt": "Mysore Palace", "state": "Karnataka", "country": "India"},
    {"prompt": "the Red Fort, Delhi", "state": "Delhi", "country": "India"},
    {"prompt": "Konark Sun Temple", "state": "Odisha", "country": "India"},
    {"prompt": "the Lotus Temple, Delhi", "state": "Delhi", "country": "India"},
    {"prompt": "Victoria Memorial, Kolkata", "state": "West Bengal", "country": "India"},
    {"prompt": "Meenakshi Temple, Madurai", "state": "Tamil Nadu", "country": "India"},
    {"prompt": "Amer Fort, Jaipur", "state": "Rajasthan", "country": "India"},
    {"prompt": "Humayun's Tomb, Delhi", "state": "Delhi", "country": "India"},
]