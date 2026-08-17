"""
Gap 4: Event Planning Domain Adaptation & Pre-built Template Engine.
Provides industry-standard event templates with rich activity DAGs, PERT estimates,
crashing data, vendor categories, and milestone markers.
"""

EVENT_TEMPLATES = {
    "WEDDING_STANDARD": {
        "name": "Grand Wedding Ceremony & Reception",
        "description": "Comprehensive scheduling template for wedding ceremony, vendor logistics, and reception.",
        "category": "WEDDING",
        "mode": "PERT",
        "activities": [
            {
                "temp_key": "A",
                "name": "Book Venue & Secure Dates",
                "category": "VENUE",
                "vendor_name": "Grand Palace Events",
                "is_milestone": True,
                "optimistic": 5, "most_likely": 7, "pessimistic": 14,
                "normal_cost": 3000, "crash_cost": 4500, "crash_dur": 4,
                "preds": []
            },
            {
                "temp_key": "B",
                "name": "Select & Contract Catering Service",
                "category": "CATERING",
                "vendor_name": "Artisan Banquet Co.",
                "is_milestone": False,
                "optimistic": 3, "most_likely": 5, "pessimistic": 8,
                "normal_cost": 2500, "crash_cost": 3200, "crash_dur": 3,
                "preds": ["A"]
            },
            {
                "temp_key": "C",
                "name": "Design & Print Invitations",
                "category": "MARKETING",
                "vendor_name": "PrintCraft Studios",
                "is_milestone": False,
                "optimistic": 2, "most_likely": 4, "pessimistic": 7,
                "normal_cost": 500, "crash_cost": 800, "crash_dur": 2,
                "preds": ["A"]
            },
            {
                "temp_key": "D",
                "name": "Floral & Theme Decor Setup",
                "category": "DECOR",
                "vendor_name": "Blossom Floral Design",
                "is_milestone": False,
                "optimistic": 1, "most_likely": 2, "pessimistic": 4,
                "normal_cost": 1200, "crash_cost": 1800, "crash_dur": 1,
                "preds": ["A"]
            },
            {
                "temp_key": "E",
                "name": "Audio Visual & DJ Sound System Setup",
                "category": "AUDIO_VISUAL",
                "vendor_name": "SoundWave Live",
                "is_milestone": False,
                "optimistic": 1, "most_likely": 2, "pessimistic": 3,
                "normal_cost": 800, "crash_cost": 1200, "crash_dur": 1,
                "preds": ["A"]
            },
            {
                "temp_key": "F",
                "name": "Distribute Invitations & RSVP Tracking",
                "category": "LOGISTICS",
                "vendor_name": "Self / Coordinator",
                "is_milestone": False,
                "optimistic": 7, "most_likely": 10, "pessimistic": 15,
                "normal_cost": 200, "crash_cost": 400, "crash_dur": 5,
                "preds": ["C"]
            },
            {
                "temp_key": "G",
                "name": "Final Menu Tasting & Headcount Confirmation",
                "category": "CATERING",
                "vendor_name": "Artisan Banquet Co.",
                "is_milestone": True,
                "optimistic": 1, "most_likely": 2, "pessimistic": 3,
                "normal_cost": 300, "crash_cost": 500, "crash_dur": 1,
                "preds": ["B", "F"]
            },
            {
                "temp_key": "H",
                "name": "Rehearsal Ceremony & Stage Walkthrough",
                "category": "LOGISTICS",
                "vendor_name": "Wedding Coordinator",
                "is_milestone": True,
                "optimistic": 1, "most_likely": 1, "pessimistic": 2,
                "normal_cost": 400, "crash_cost": 600, "crash_dur": 1,
                "preds": ["D", "E"]
            },
            {
                "temp_key": "I",
                "name": "Event Execution & Wedding Reception",
                "category": "EVENT_EXECUTION",
                "vendor_name": "Main Venue & All Vendors",
                "is_milestone": True,
                "optimistic": 1, "most_likely": 1, "pessimistic": 1,
                "normal_cost": 5000, "crash_cost": 5000, "crash_dur": 1,
                "preds": ["G", "H"]
            }
        ]
    },
    "TECH_CONFERENCE": {
        "name": "Annual Tech Conference & Expo",
        "description": "Standard corporate conference layout covering keynote speakers, sponsorships, AV setup, and live streaming.",
        "category": "CONFERENCE",
        "mode": "CPM",
        "activities": [
            {
                "temp_key": "A",
                "name": "Convention Center Booking",
                "category": "VENUE",
                "vendor_name": "City Expo Center",
                "is_milestone": True,
                "optimistic": 10, "most_likely": 10, "pessimistic": 10,
                "duration": 10, "normal_cost": 10000, "crash_cost": 15000, "crash_dur": 7,
                "preds": []
            },
            {
                "temp_key": "B",
                "name": "Keynote Speaker Confirmation",
                "category": "ENTERTAINMENT",
                "vendor_name": "Tech Speakers Agency",
                "is_milestone": True,
                "optimistic": 8, "most_likely": 8, "pessimistic": 8,
                "duration": 8, "normal_cost": 5000, "crash_cost": 8000, "crash_dur": 4,
                "preds": ["A"]
            },
            {
                "temp_key": "C",
                "name": "Sponsorship Packages & Booth Sales",
                "category": "MARKETING",
                "vendor_name": "Sales Team",
                "is_milestone": False,
                "optimistic": 12, "most_likely": 12, "pessimistic": 12,
                "duration": 12, "normal_cost": 2000, "crash_cost": 4000, "crash_dur": 8,
                "preds": ["A"]
            },
            {
                "temp_key": "D",
                "name": "Stage Rigging & AV Setup",
                "category": "AUDIO_VISUAL",
                "vendor_name": "ProAV Media",
                "is_milestone": False,
                "optimistic": 3, "most_likely": 3, "pessimistic": 3,
                "duration": 3, "normal_cost": 4000, "crash_cost": 6000, "crash_dur": 2,
                "preds": ["B"]
            },
            {
                "temp_key": "E",
                "name": "Live Streaming & Network Testing",
                "category": "AUDIO_VISUAL",
                "vendor_name": "StreamNet Systems",
                "is_milestone": False,
                "optimistic": 2, "most_likely": 2, "pessimistic": 2,
                "duration": 2, "normal_cost": 1500, "crash_cost": 2500, "crash_dur": 1,
                "preds": ["D"]
            },
            {
                "temp_key": "F",
                "name": "Conference Day Execution",
                "category": "EVENT_EXECUTION",
                "vendor_name": "All Vendors",
                "is_milestone": True,
                "optimistic": 1, "most_likely": 1, "pessimistic": 1,
                "duration": 1, "normal_cost": 12000, "crash_cost": 12000, "crash_dur": 1,
                "preds": ["C", "E"]
            }
        ]
    }
}
