"""Business type registry — a single source of truth for:

- the list of business types we support (Business.business_type choices)
- their default category set on the customer review page
- per-type vocabulary + style hints we inject into the AI prompt so the
  model talks about things real customers of that kind of business
  actually talk about (a hardware store gets "stock availability, pricing,
  staff knowledge"; a clinic gets "doctor, wait time, cleanliness").

Do not hardcode this list anywhere else — import from here.
"""

from __future__ import annotations


# Each entry:
#   label               — English label shown in pickers
#   group               — industry section for grouped UI
#   default_categories  — [{key, label}, …] shown as chips on the customer page
#   vocabulary_hints    — comma-separated terms the AI should consider
#   style_hints         — 1-2 sentence nudge about how real customers talk
#
# Group order is the order they appear in the onboarding picker.

TYPE_REGISTRY: dict[str, dict] = {
    # ---------- Food & Beverage ----------
    "restaurant": {
        "label": "Restaurant",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "food", "label": "Food"},
            {"key": "staff", "label": "Staff"},
            {"key": "service", "label": "Service"},
            {"key": "ambiance", "label": "Ambiance"},
            {"key": "value", "label": "Value for money"},
        ],
        "vocabulary_hints": "specific dishes, flavour, spice level, portion size, freshness, hot/cold food, wait time, hygiene, family seating, parking",
        "style_hints": "Real customers mention one or two dishes by name, how the food actually tasted, how long they waited, and whether the bill felt fair. They don't say 'amazing food' — they describe the paneer or the biryani.",
    },
    "cafe": {
        "label": "Café / Coffee shop",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "coffee", "label": "Coffee / drinks"},
            {"key": "snacks", "label": "Snacks"},
            {"key": "ambiance", "label": "Ambiance"},
            {"key": "wifi_workspace", "label": "Wifi / workspace"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "cappuccino, latte art, cold brew, cookies, sandwiches, seating, plug points, wifi, study spot, hangout",
        "style_hints": "Customers mention specific drinks and whether they stayed to work or just grab-and-go. Mention of plug points / wifi is common.",
    },
    "bar_pub": {
        "label": "Bar / Pub",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "drinks", "label": "Drinks"},
            {"key": "food", "label": "Food"},
            {"key": "ambiance", "label": "Ambiance / music"},
            {"key": "staff", "label": "Staff"},
            {"key": "value", "label": "Pricing"},
        ],
        "vocabulary_hints": "cocktails, beer, whiskey, music, crowd, bar bites, happy hours, seating",
        "style_hints": "People talk about vibe and crowd more than food. Mention of specific cocktails/draught and whether the music was too loud is common.",
    },
    "bakery": {
        "label": "Bakery",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "freshness", "label": "Freshness"},
            {"key": "variety", "label": "Variety"},
            {"key": "taste", "label": "Taste"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "packaging", "label": "Packaging"},
        ],
        "vocabulary_hints": "cake, pastry, bread, puff, birthday cake, customisation, eggless, fresh, warm",
        "style_hints": "Mention a specific item (cake/pastry/bread), whether it was fresh, and the pricing compared to local bakeries.",
    },
    "sweet_shop": {
        "label": "Sweet shop (Mithai)",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "taste", "label": "Taste"},
            {"key": "freshness", "label": "Freshness"},
            {"key": "variety", "label": "Variety"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "packaging", "label": "Packaging"},
        ],
        "vocabulary_hints": "kaju katli, rasgulla, jalebi, besan laddu, dry fruits, milk sweets, festive, gift box, shuddh ghee",
        "style_hints": "Customers talk about one or two specific mithai, whether it's fresh, and whether it used real ghee. Festivals/gifting are common contexts.",
    },
    "ice_cream_parlour": {
        "label": "Ice cream / dessert parlour",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "flavours", "label": "Flavours"},
            {"key": "taste", "label": "Taste"},
            {"key": "serving", "label": "Serving size"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "scoops, sundae, shake, waffle, flavour variety, serving size",
        "style_hints": "Mention a specific flavour or combo. Family/kids context is common.",
    },
    "fast_food": {
        "label": "Fast food / QSR",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "taste", "label": "Taste"},
            {"key": "speed", "label": "Speed of service"},
            {"key": "value", "label": "Value"},
            {"key": "hygiene", "label": "Hygiene"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "burger, pizza, wrap, fries, combo, quick bite, takeaway, delivery",
        "style_hints": "Speed and value matter more than ambiance. Specific combo mentions are common.",
    },
    "food_truck": {
        "label": "Food truck / Street-style",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "taste", "label": "Taste"},
            {"key": "value", "label": "Value"},
            {"key": "hygiene", "label": "Hygiene"},
            {"key": "variety", "label": "Variety"},
        ],
        "vocabulary_hints": "chaat, pav bhaji, vada pav, rolls, momos, quick bite, affordable",
        "style_hints": "Expect casual language. Price and taste dominate. Hygiene sometimes surprises customers positively.",
    },
    "tiffin_service": {
        "label": "Tiffin / Home food service",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "taste", "label": "Taste"},
            {"key": "consistency", "label": "Day-to-day consistency"},
            {"key": "timeliness", "label": "On-time delivery"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "variety", "label": "Menu variety"},
        ],
        "vocabulary_hints": "ghar ka khana, roti sabzi, dal rice, monthly plan, timely delivery, hygienic packaging",
        "style_hints": "Working professionals, students, hostels. Talks about consistency day-to-day and delivery time.",
    },
    "juice_bar": {
        "label": "Juice / Shake bar",
        "group": "Food & Beverage",
        "default_categories": [
            {"key": "freshness", "label": "Freshness"},
            {"key": "variety", "label": "Variety"},
            {"key": "hygiene", "label": "Hygiene"},
            {"key": "pricing", "label": "Pricing"},
        ],
        "vocabulary_hints": "fresh juice, smoothie, shake, seasonal fruit, hygienic, quick",
        "style_hints": "Freshness and hygiene are top concerns. Mention of specific fruit/combo is common.",
    },

    # ---------- Hospitality ----------
    "hotel": {
        "label": "Hotel",
        "group": "Hospitality",
        "default_categories": [
            {"key": "rooms", "label": "Rooms"},
            {"key": "staff", "label": "Staff"},
            {"key": "cleanliness", "label": "Cleanliness"},
            {"key": "food", "label": "Food"},
            {"key": "location", "label": "Location"},
            {"key": "value", "label": "Value"},
        ],
        "vocabulary_hints": "check-in, room size, AC, bathroom, breakfast, reception, housekeeping, booking, view, quiet",
        "style_hints": "Guests compare against expectations set by the booking photos. Specific staff helpfulness and breakfast quality are frequent touch-points.",
    },
    "guesthouse_lodge": {
        "label": "Guesthouse / Lodge",
        "group": "Hospitality",
        "default_categories": [
            {"key": "rooms", "label": "Rooms"},
            {"key": "cleanliness", "label": "Cleanliness"},
            {"key": "staff", "label": "Staff"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "location", "label": "Location"},
        ],
        "vocabulary_hints": "budget stay, basic, clean, walking distance, bus stand, railway station, night halt",
        "style_hints": "Budget traveller voice. Pragmatic — 'clean enough', 'near station'.",
    },
    "resort": {
        "label": "Resort",
        "group": "Hospitality",
        "default_categories": [
            {"key": "rooms", "label": "Rooms"},
            {"key": "food", "label": "Food"},
            {"key": "activities", "label": "Activities"},
            {"key": "staff", "label": "Staff"},
            {"key": "value", "label": "Value"},
        ],
        "vocabulary_hints": "weekend getaway, pool, nature, activities, kids, buffet, rooms with view",
        "style_hints": "Weekend/family getaway context. Pool, food, and kids' activities dominate.",
    },
    "homestay": {
        "label": "Homestay / Bed & Breakfast",
        "group": "Hospitality",
        "default_categories": [
            {"key": "host", "label": "Host / family"},
            {"key": "rooms", "label": "Rooms"},
            {"key": "food", "label": "Home food"},
            {"key": "cleanliness", "label": "Cleanliness"},
            {"key": "location", "label": "Location"},
        ],
        "vocabulary_hints": "host family, home-cooked meals, warm welcome, local tips, authentic stay",
        "style_hints": "Personal, warm tone. Host name / family is often mentioned. Home food is a star.",
    },

    # ---------- Health & Wellness ----------
    "clinic": {
        "label": "Clinic / Doctor",
        "group": "Health & Wellness",
        "default_categories": [
            {"key": "doctor", "label": "Doctor"},
            {"key": "staff", "label": "Staff"},
            {"key": "wait_time", "label": "Wait time"},
            {"key": "cleanliness", "label": "Cleanliness"},
            {"key": "fees", "label": "Fees"},
        ],
        "vocabulary_hints": "diagnosis, patient care, appointment, punctual, waiting area, prescription, follow-up, listens patiently",
        "style_hints": "Calm, grateful voice. Patients appreciate doctors who listen and don't rush them. Mention wait time honestly.",
    },
    "dental_clinic": {
        "label": "Dental clinic",
        "group": "Health & Wellness",
        "default_categories": [
            {"key": "doctor", "label": "Dentist"},
            {"key": "procedure_quality", "label": "Procedure / treatment"},
            {"key": "cleanliness", "label": "Hygiene"},
            {"key": "pain_management", "label": "Pain management"},
            {"key": "fees", "label": "Fees"},
        ],
        "vocabulary_hints": "cleaning, RCT, cavity, filling, painless, injection, pricing, hygiene, aftercare",
        "style_hints": "Relief at 'it didn't hurt' is a common thread. Patients mention the specific procedure.",
    },
    "hospital": {
        "label": "Hospital / Multi-specialty",
        "group": "Health & Wellness",
        "default_categories": [
            {"key": "doctor", "label": "Doctors"},
            {"key": "nursing", "label": "Nursing / staff"},
            {"key": "cleanliness", "label": "Cleanliness"},
            {"key": "facilities", "label": "Facilities"},
            {"key": "billing", "label": "Billing transparency"},
        ],
        "vocabulary_hints": "admission, consultation, surgery, nurses, ward, ICU, discharge, insurance, billing",
        "style_hints": "Mix of gratitude and practical details about nursing, facilities, billing.",
    },
    "diagnostics_lab": {
        "label": "Diagnostics / Pathology lab",
        "group": "Health & Wellness",
        "default_categories": [
            {"key": "accuracy", "label": "Report accuracy"},
            {"key": "turnaround", "label": "Report turnaround"},
            {"key": "staff", "label": "Staff"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "home_collection", "label": "Home collection"},
        ],
        "vocabulary_hints": "blood test, report on time, sample collection, technician, home visit, pricing",
        "style_hints": "Focus on timeliness, clarity of report, and whether home collection was on time.",
    },
    "pharmacy": {
        "label": "Pharmacy / Medical store",
        "group": "Health & Wellness",
        "default_categories": [
            {"key": "stock", "label": "Stock availability"},
            {"key": "staff_knowledge", "label": "Staff knowledge"},
            {"key": "pricing", "label": "Pricing / discount"},
            {"key": "delivery", "label": "Delivery"},
            {"key": "trust", "label": "Trust / genuineness"},
        ],
        "vocabulary_hints": "medicines available, prescription, generic, discount, home delivery, bill, 24 hours",
        "style_hints": "Brief, practical: did they have the medicine, honest pricing, and was delivery fast.",
    },
    "veterinary": {
        "label": "Veterinary clinic / Pet",
        "group": "Health & Wellness",
        "default_categories": [
            {"key": "vet", "label": "Vet / doctor"},
            {"key": "handling", "label": "Pet handling"},
            {"key": "cleanliness", "label": "Cleanliness"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "dog, cat, vaccination, grooming, surgery, follow-up, patient with pets",
        "style_hints": "Pet owner voice. Mentions pet's name and whether vet was gentle/patient.",
    },
    "optical_store": {
        "label": "Optical store",
        "group": "Health & Wellness",
        "default_categories": [
            {"key": "product_variety", "label": "Frames / lenses"},
            {"key": "eye_test", "label": "Eye test"},
            {"key": "staff", "label": "Staff"},
            {"key": "pricing", "label": "Pricing"},
        ],
        "vocabulary_hints": "eye test, frame selection, power, lenses, fitting, warranty, delivery time",
        "style_hints": "Mentions frame selection, whether the power was correct, and fit after delivery.",
    },

    # ---------- Beauty & Personal Care ----------
    "salon": {
        "label": "Salon / Beauty parlour",
        "group": "Beauty & Personal Care",
        "default_categories": [
            {"key": "skill", "label": "Skill / results"},
            {"key": "hygiene", "label": "Hygiene"},
            {"key": "staff", "label": "Staff"},
            {"key": "ambiance", "label": "Ambiance"},
            {"key": "pricing", "label": "Pricing"},
        ],
        "vocabulary_hints": "haircut, facial, hair colour, threading, manicure, pedicure, waxing, bridal, hygienic",
        "style_hints": "Customers mention the specific service and whether the result matched what they asked for.",
    },
    "spa": {
        "label": "Spa / Massage",
        "group": "Beauty & Personal Care",
        "default_categories": [
            {"key": "therapist_skill", "label": "Therapist skill"},
            {"key": "ambiance", "label": "Ambiance / relaxation"},
            {"key": "hygiene", "label": "Hygiene"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "deep tissue, aroma, steam, sauna, calming music, clean linen, body pain relief",
        "style_hints": "Calm, relieved tone. Mentions technique and whether pain/stiffness actually improved.",
    },
    "barber_shop": {
        "label": "Barber shop",
        "group": "Beauty & Personal Care",
        "default_categories": [
            {"key": "haircut_quality", "label": "Haircut / beard"},
            {"key": "speed", "label": "Speed"},
            {"key": "hygiene", "label": "Hygiene"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "haircut, beard trim, shave, fade, massage, fresh towel, blade, clean chair",
        "style_hints": "Casual, direct. Mentions the style/fade, hygiene (fresh blade), and time taken.",
    },
    "nail_studio": {
        "label": "Nail studio",
        "group": "Beauty & Personal Care",
        "default_categories": [
            {"key": "skill", "label": "Skill / design"},
            {"key": "hygiene", "label": "Hygiene"},
            {"key": "durability", "label": "Longevity"},
            {"key": "pricing", "label": "Pricing"},
        ],
        "vocabulary_hints": "gel, acrylic, extensions, nail art, tools sterilised, chipping",
        "style_hints": "Mentions specific design, whether it lasted, hygiene of tools.",
    },
    "mehendi_artist": {
        "label": "Mehendi / Henna artist",
        "group": "Beauty & Personal Care",
        "default_categories": [
            {"key": "design", "label": "Design / detail"},
            {"key": "colour", "label": "Colour depth"},
            {"key": "timeliness", "label": "On-time"},
            {"key": "pricing", "label": "Pricing"},
        ],
        "vocabulary_hints": "bridal, Arabic, Rajasthani, dark colour, design detail, event, on time",
        "style_hints": "Wedding / event context. Mentions colour depth and design intricacy.",
    },

    # ---------- Fitness ----------
    "gym": {
        "label": "Gym / Fitness centre",
        "group": "Fitness",
        "default_categories": [
            {"key": "equipment", "label": "Equipment"},
            {"key": "trainers", "label": "Trainers"},
            {"key": "cleanliness", "label": "Cleanliness"},
            {"key": "crowd", "label": "Crowd / timing"},
            {"key": "pricing", "label": "Pricing"},
        ],
        "vocabulary_hints": "cardio, weights, dumbbells, trainer guidance, AC, shower, personal training, membership",
        "style_hints": "Mentions specific equipment, trainer by demeanour, and how crowded peak hours feel.",
    },
    "yoga_studio": {
        "label": "Yoga studio",
        "group": "Fitness",
        "default_categories": [
            {"key": "instructor", "label": "Instructor"},
            {"key": "space", "label": "Space / ambiance"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "variety", "label": "Class variety"},
        ],
        "vocabulary_hints": "asana, pranayama, calm, instructor patient, beginner, flexibility, meditation",
        "style_hints": "Calm, reflective. Progress in flexibility/breathing is common.",
    },
    "fitness_trainer": {
        "label": "Personal trainer / Coach",
        "group": "Fitness",
        "default_categories": [
            {"key": "expertise", "label": "Expertise"},
            {"key": "results", "label": "Results"},
            {"key": "motivation", "label": "Motivation"},
            {"key": "pricing", "label": "Pricing"},
        ],
        "vocabulary_hints": "weight loss, muscle gain, diet plan, personalised, push you, results in months",
        "style_hints": "Transformation story in a sentence or two. Mentions before/after feel.",
    },
    "dance_studio": {
        "label": "Dance / Music studio",
        "group": "Fitness",
        "default_categories": [
            {"key": "instructor", "label": "Instructor"},
            {"key": "learning", "label": "Learning experience"},
            {"key": "space", "label": "Space"},
            {"key": "pricing", "label": "Pricing"},
        ],
        "vocabulary_hints": "classical, hip hop, bollywood, instrument, beginner friendly, performance, recital",
        "style_hints": "Parent-for-kid or adult-learner voice. Progress and confidence building are common.",
    },

    # ---------- Retail ----------
    "retail": {
        "label": "Retail store (general)",
        "group": "Retail",
        "default_categories": [
            {"key": "products", "label": "Products"},
            {"key": "staff", "label": "Staff"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "variety", "label": "Variety / stock"},
        ],
        "vocabulary_hints": "product range, staff helpful, price, stock, quality, billing",
        "style_hints": "Mentions what they bought and whether staff helped them find the right thing.",
    },
    "kirana_store": {
        "label": "Kirana / Grocery store",
        "group": "Retail",
        "default_categories": [
            {"key": "stock", "label": "Stock availability"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "owner", "label": "Owner / staff"},
            {"key": "home_delivery", "label": "Home delivery"},
        ],
        "vocabulary_hints": "daily needs, rates, home delivery, credit khaata, fresh, bhaiya, uncle",
        "style_hints": "Neighbourhood familiarity. Calls the owner 'bhaiya'/'uncle'. Mentions credit/home delivery.",
    },
    "supermarket": {
        "label": "Supermarket",
        "group": "Retail",
        "default_categories": [
            {"key": "variety", "label": "Variety"},
            {"key": "pricing", "label": "Pricing / offers"},
            {"key": "freshness", "label": "Fresh produce"},
            {"key": "staff", "label": "Staff"},
            {"key": "billing", "label": "Billing speed"},
        ],
        "vocabulary_hints": "offers, discount, fresh fruits, cleaning supplies, parking, billing queue",
        "style_hints": "Family shopping. Mentions offers, fresh produce, and billing queue.",
    },
    "clothing_store": {
        "label": "Clothing / Apparel store",
        "group": "Retail",
        "default_categories": [
            {"key": "variety", "label": "Variety / designs"},
            {"key": "quality", "label": "Quality"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "staff", "label": "Staff"},
            {"key": "trial_rooms", "label": "Trial rooms"},
        ],
        "vocabulary_hints": "designs, fitting, fabric, trial room, latest trend, ethnic, western, wedding",
        "style_hints": "Mentions an occasion they shopped for, design variety, and trial room experience.",
    },
    "jewelry_store": {
        "label": "Jewellery store",
        "group": "Retail",
        "default_categories": [
            {"key": "trust", "label": "Trust / purity"},
            {"key": "design", "label": "Design variety"},
            {"key": "pricing", "label": "Pricing / making charges"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "gold, silver, bis hallmark, making charges, design, bridal, daily wear, trust",
        "style_hints": "Trust/authenticity is the biggest factor. Mentions hallmark, making charges, staff patience.",
    },
    "electronics_store": {
        "label": "Electronics store",
        "group": "Retail",
        "default_categories": [
            {"key": "product_range", "label": "Product range"},
            {"key": "staff_knowledge", "label": "Staff knowledge"},
            {"key": "pricing", "label": "Pricing / deals"},
            {"key": "warranty_support", "label": "Warranty / support"},
        ],
        "vocabulary_hints": "TV, fridge, washing machine, AC, warranty, demo, installation, delivery",
        "style_hints": "Mentions the specific product purchased and whether delivery/installation was on time.",
    },
    "mobile_shop": {
        "label": "Mobile / Phone store",
        "group": "Retail",
        "default_categories": [
            {"key": "variety", "label": "Brand variety"},
            {"key": "staff_knowledge", "label": "Staff knowledge"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "exchange_offer", "label": "Exchange / offers"},
        ],
        "vocabulary_hints": "iPhone, Samsung, Redmi, accessories, screen guard, exchange, finance, EMI",
        "style_hints": "Mentions the phone model bought, exchange/EMI deal, and accessory bundles.",
    },
    "footwear_store": {
        "label": "Footwear / Shoe store",
        "group": "Retail",
        "default_categories": [
            {"key": "variety", "label": "Variety"},
            {"key": "quality", "label": "Quality"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "fitting", "label": "Fitting"},
        ],
        "vocabulary_hints": "sports shoes, formal, casual, size, comfort, walking, brand",
        "style_hints": "Mentions comfort after walking, whether the size was right, and value.",
    },
    "cosmetics_shop": {
        "label": "Cosmetics / Beauty shop",
        "group": "Retail",
        "default_categories": [
            {"key": "variety", "label": "Brand variety"},
            {"key": "authenticity", "label": "Authentic products"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "lipstick, foundation, skincare, brand, authentic, hygienic, staff suggestion",
        "style_hints": "Authenticity and brand range matter. Staff suggestions often noted.",
    },
    "hardware_store": {
        "label": "Hardware store",
        "group": "Retail",
        "default_categories": [
            {"key": "stock", "label": "Stock availability"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "staff_knowledge", "label": "Staff knowledge"},
            {"key": "delivery", "label": "Delivery / loading"},
            {"key": "quality", "label": "Quality"},
        ],
        "vocabulary_hints": "cement, tiles, pipes, paint, electrical fittings, tools, delivery truck, rate, bulk order",
        "style_hints": "Contractor/homeowner voice. Very practical — whether the exact item was in stock, pricing vs market, and on-time delivery.",
    },
    "book_stationery": {
        "label": "Book / Stationery store",
        "group": "Retail",
        "default_categories": [
            {"key": "variety", "label": "Variety"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "staff", "label": "Staff"},
            {"key": "school_supplies", "label": "School supplies"},
        ],
        "vocabulary_hints": "textbooks, notebook, pen, stationery, school list, gifts, competitive exam books",
        "style_hints": "Students and parents. Mentions specific textbooks/stationery and whether the shop had the school list.",
    },
    "furniture_store": {
        "label": "Furniture / Home decor",
        "group": "Retail",
        "default_categories": [
            {"key": "quality", "label": "Quality"},
            {"key": "design", "label": "Design / variety"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "delivery", "label": "Delivery / assembly"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "sofa, bed, dining table, polish, assembly, wooden, modular, customisation",
        "style_hints": "Customers mention the piece, finish quality, and whether assembly/delivery was smooth.",
    },
    "agri_seed_store": {
        "label": "Agri / Seed / Fertiliser",
        "group": "Retail",
        "default_categories": [
            {"key": "product_range", "label": "Product range"},
            {"key": "advice", "label": "Farming advice"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "delivery", "label": "Delivery"},
        ],
        "vocabulary_hints": "seeds, fertiliser, pesticide, cotton, wheat, tractor parts, proper guidance, rate",
        "style_hints": "Farmer voice. Mentions the crop, whether the shopkeeper gave proper advice, and rates.",
    },

    # ---------- Automotive ----------
    "car_service": {
        "label": "Car service / Garage",
        "group": "Automotive",
        "default_categories": [
            {"key": "workmanship", "label": "Workmanship"},
            {"key": "honesty", "label": "Honest pricing"},
            {"key": "turnaround", "label": "Time taken"},
            {"key": "staff", "label": "Staff"},
            {"key": "parts", "label": "Parts availability"},
        ],
        "vocabulary_hints": "service, oil change, alignment, denting painting, puncture, battery, genuine parts, same-day",
        "style_hints": "Practical/trust-based. Customers prize honest pricing and 'no unnecessary work'. Mention the actual problem fixed.",
    },
    "bike_service": {
        "label": "Bike / Two-wheeler service",
        "group": "Automotive",
        "default_categories": [
            {"key": "workmanship", "label": "Workmanship"},
            {"key": "honesty", "label": "Honest pricing"},
            {"key": "turnaround", "label": "Time taken"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "engine oil, chain, brakes, clutch, tyre, running smooth, pickup",
        "style_hints": "Quick visits. Mentions running smoothness and honest diagnosis.",
    },
    "car_wash": {
        "label": "Car / Bike wash",
        "group": "Automotive",
        "default_categories": [
            {"key": "cleaning_quality", "label": "Cleaning quality"},
            {"key": "speed", "label": "Speed"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "foam wash, interior cleaning, polish, quick, dust-free, rate",
        "style_hints": "Quick, functional. Mentions how clean the interior was.",
    },
    "petrol_pump": {
        "label": "Petrol pump / Fuel station",
        "group": "Automotive",
        "default_categories": [
            {"key": "measure_honesty", "label": "Measure / honesty"},
            {"key": "staff_behavior", "label": "Staff behavior"},
            {"key": "speed", "label": "Speed"},
            {"key": "cleanliness", "label": "Cleanliness / toilets"},
        ],
        "vocabulary_hints": "full tank, measure zero, air, toilet, clean, polite, card payment",
        "style_hints": "Trust-focused: did they show zero, was air free. Short, factual.",
    },
    "car_dealer": {
        "label": "Car / Vehicle dealership",
        "group": "Automotive",
        "default_categories": [
            {"key": "staff", "label": "Staff / sales"},
            {"key": "test_drive", "label": "Test drive experience"},
            {"key": "pricing", "label": "Pricing / finance"},
            {"key": "delivery", "label": "Delivery experience"},
        ],
        "vocabulary_hints": "test drive, finance, down payment, EMI, delivery, registration, accessories",
        "style_hints": "Buying-a-car excitement. Mentions salesperson by name and delivery day feel.",
    },

    # ---------- Home Services ----------
    "plumber": {
        "label": "Plumber",
        "group": "Home Services",
        "default_categories": [
            {"key": "workmanship", "label": "Work quality"},
            {"key": "timeliness", "label": "On-time"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "cleanup", "label": "Clean-up after work"},
        ],
        "vocabulary_hints": "leakage, tap, bathroom, pipes, motor, overhead tank, sincere work",
        "style_hints": "Homeowner voice. Mentions the exact fix (leak, tap) and whether they cleaned up.",
    },
    "electrician": {
        "label": "Electrician",
        "group": "Home Services",
        "default_categories": [
            {"key": "workmanship", "label": "Work quality"},
            {"key": "timeliness", "label": "On-time"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "safety", "label": "Safety"},
        ],
        "vocabulary_hints": "wiring, switchboard, fan installation, MCB, short circuit, neat wiring",
        "style_hints": "Mentions the specific job and whether wiring looked neat/safe.",
    },
    "carpenter": {
        "label": "Carpenter",
        "group": "Home Services",
        "default_categories": [
            {"key": "workmanship", "label": "Finish quality"},
            {"key": "timeliness", "label": "On-time"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "material", "label": "Material quality"},
        ],
        "vocabulary_hints": "wardrobe, modular kitchen, polish, plywood, door, customisation, finish",
        "style_hints": "Mentions the piece built and the finish quality.",
    },
    "painter_contractor": {
        "label": "Painter / Contractor",
        "group": "Home Services",
        "default_categories": [
            {"key": "workmanship", "label": "Finish quality"},
            {"key": "timeliness", "label": "On-time"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "cleanup", "label": "Clean-up"},
        ],
        "vocabulary_hints": "paint, putty, texture, smooth finish, colour match, cover furniture, cleanup",
        "style_hints": "Home renovation context. Finish smoothness, and whether the site was kept clean.",
    },
    "cleaning_service": {
        "label": "Home cleaning / Pest control",
        "group": "Home Services",
        "default_categories": [
            {"key": "thoroughness", "label": "Thoroughness"},
            {"key": "staff", "label": "Staff"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "safety", "label": "Safety / chemicals"},
        ],
        "vocabulary_hints": "deep cleaning, kitchen, bathroom, sofa, chemicals, safe for kids, pest free",
        "style_hints": "Mentions rooms cleaned, thoroughness, and whether chemicals felt safe.",
    },

    # ---------- Education ----------
    "school": {
        "label": "School",
        "group": "Education",
        "default_categories": [
            {"key": "teaching", "label": "Teaching quality"},
            {"key": "staff", "label": "Staff / admin"},
            {"key": "facilities", "label": "Facilities"},
            {"key": "discipline", "label": "Discipline / safety"},
            {"key": "fees", "label": "Fees"},
        ],
        "vocabulary_hints": "teachers, curriculum, activities, sports, discipline, fees structure, safety, parent meeting",
        "style_hints": "Parent voice. Mentions teacher warmth, discipline, and extracurriculars.",
    },
    "coaching_institute": {
        "label": "Coaching institute",
        "group": "Education",
        "default_categories": [
            {"key": "faculty", "label": "Faculty"},
            {"key": "results", "label": "Results"},
            {"key": "study_material", "label": "Study material"},
            {"key": "fees", "label": "Fees"},
            {"key": "doubt_support", "label": "Doubt support"},
        ],
        "vocabulary_hints": "JEE, NEET, UPSC, mock tests, doubt sessions, faculty experienced, results",
        "style_hints": "Student/parent voice. Mentions specific exams, mock test frequency, and doubt support.",
    },
    "tuition_classes": {
        "label": "Tuition classes",
        "group": "Education",
        "default_categories": [
            {"key": "teacher", "label": "Teacher"},
            {"key": "improvement", "label": "Improvement seen"},
            {"key": "fees", "label": "Fees"},
            {"key": "timing", "label": "Timing / batch"},
        ],
        "vocabulary_hints": "board exam, maths, science, homework help, patient teacher, small batch",
        "style_hints": "Parent of school-going child. Mentions subject, and whether marks actually improved.",
    },
    "preschool_daycare": {
        "label": "Preschool / Daycare",
        "group": "Education",
        "default_categories": [
            {"key": "teachers", "label": "Teachers"},
            {"key": "safety", "label": "Safety / hygiene"},
            {"key": "activities", "label": "Activities"},
            {"key": "food", "label": "Food"},
            {"key": "fees", "label": "Fees"},
        ],
        "vocabulary_hints": "kids, caretakers, playtime, safe, cctv, nutritious food, parents updates",
        "style_hints": "Parent voice. Safety, affection from teachers, and activities dominate.",
    },

    # ---------- Professional & Other ----------
    "photography_studio": {
        "label": "Photography studio",
        "group": "Professional & Other",
        "default_categories": [
            {"key": "creativity", "label": "Creativity"},
            {"key": "professionalism", "label": "Professionalism"},
            {"key": "delivery_speed", "label": "Delivery speed"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "equipment", "label": "Equipment / quality"},
        ],
        "vocabulary_hints": "wedding, pre-wedding, candid, album, editing, delivery, professional, makes you comfortable",
        "style_hints": "Event/wedding context. Mentions specific shots/albums and editing delivery time.",
    },
    "event_wedding_planner": {
        "label": "Event / Wedding planner",
        "group": "Professional & Other",
        "default_categories": [
            {"key": "planning", "label": "Planning"},
            {"key": "execution", "label": "Execution"},
            {"key": "vendors", "label": "Vendor network"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "communication", "label": "Communication"},
        ],
        "vocabulary_hints": "wedding, decor, catering, co-ordinator, stress-free, last-minute, attention to detail",
        "style_hints": "Gratitude-heavy. Talks about specific decor/food and stress handled by planner.",
    },
    "travel_agency": {
        "label": "Travel agency / Tour",
        "group": "Professional & Other",
        "default_categories": [
            {"key": "planning", "label": "Itinerary / planning"},
            {"key": "pricing", "label": "Pricing / transparency"},
            {"key": "support", "label": "On-trip support"},
            {"key": "communication", "label": "Communication"},
        ],
        "vocabulary_hints": "trip, package, hotel bookings, itinerary, group tour, visa, no hidden charges",
        "style_hints": "Mentions destination, whether hotel/transfers were smooth, and responsiveness on-trip.",
    },
    "real_estate_agent": {
        "label": "Real estate / Property",
        "group": "Professional & Other",
        "default_categories": [
            {"key": "honesty", "label": "Honesty"},
            {"key": "options", "label": "Options shown"},
            {"key": "responsiveness", "label": "Responsiveness"},
            {"key": "paperwork", "label": "Paperwork help"},
        ],
        "vocabulary_hints": "rent, sale, flat, plot, documents, brokerage, legal verification, transparent",
        "style_hints": "Trust-first. Mentions honesty about defects, help with documentation.",
    },
    "tailor": {
        "label": "Tailor / Boutique",
        "group": "Professional & Other",
        "default_categories": [
            {"key": "fit", "label": "Fit / measurement"},
            {"key": "finish", "label": "Finish / stitching"},
            {"key": "timeliness", "label": "On-time"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "design", "label": "Design / customisation"},
        ],
        "vocabulary_hints": "measurement, fitting, blouse, suit, alteration, delivery, stitching, custom",
        "style_hints": "Mentions fit and finish. Alteration/delivery timing is common.",
    },
    "laundry_drycleaner": {
        "label": "Laundry / Dry cleaner",
        "group": "Professional & Other",
        "default_categories": [
            {"key": "cleaning_quality", "label": "Cleaning quality"},
            {"key": "turnaround", "label": "Turnaround"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "care", "label": "Care with clothes"},
        ],
        "vocabulary_hints": "stain, dry clean, ironing, delivery, pickup, curtains, wedding outfit",
        "style_hints": "Mentions specific clothing item and whether it came back clean/undamaged.",
    },

    # ---------- Repair ----------
    "mobile_repair": {
        "label": "Mobile repair",
        "group": "Repair",
        "default_categories": [
            {"key": "diagnosis", "label": "Diagnosis"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "turnaround", "label": "Turnaround"},
            {"key": "parts", "label": "Parts quality"},
            {"key": "staff", "label": "Staff"},
        ],
        "vocabulary_hints": "screen replacement, battery, charging port, water damage, original parts, warranty",
        "style_hints": "Mentions the phone/issue, original vs duplicate parts, and whether it worked after repair.",
    },
    "computer_repair": {
        "label": "Computer / Laptop repair",
        "group": "Repair",
        "default_categories": [
            {"key": "diagnosis", "label": "Diagnosis"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "turnaround", "label": "Turnaround"},
            {"key": "data_safety", "label": "Data safety"},
        ],
        "vocabulary_hints": "laptop, hard disk, SSD, RAM, formatted, data backup, software install, virus",
        "style_hints": "Mentions the specific issue and whether data was preserved.",
    },
    "appliance_repair": {
        "label": "Appliance / AC repair",
        "group": "Repair",
        "default_categories": [
            {"key": "workmanship", "label": "Work quality"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "turnaround", "label": "Time taken"},
            {"key": "parts", "label": "Parts used"},
        ],
        "vocabulary_hints": "AC service, refrigerator, washing machine, microwave, gas refill, genuine parts, warranty on work",
        "style_hints": "Mentions the appliance and the fix. Honest pricing is the trust signal.",
    },
    "watch_repair": {
        "label": "Watch / Jewellery repair",
        "group": "Repair",
        "default_categories": [
            {"key": "workmanship", "label": "Work quality"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "turnaround", "label": "Turnaround"},
        ],
        "vocabulary_hints": "battery, servicing, strap, scratch, polish, cleaning",
        "style_hints": "Short, practical. Mentions the brand/item and whether it's running well.",
    },

    # ---------- Catch-all ----------
    "other": {
        "label": "Other",
        "group": "Other",
        "default_categories": [
            {"key": "quality", "label": "Quality"},
            {"key": "staff", "label": "Staff"},
            {"key": "pricing", "label": "Pricing"},
            {"key": "service", "label": "Service"},
        ],
        "vocabulary_hints": "quality, staff, pricing, service",
        "style_hints": "Use generic but grounded language. Refer to what the customer actually received.",
    },
}


# Order of groups in the onboarding picker
GROUP_ORDER = [
    "Food & Beverage",
    "Hospitality",
    "Health & Wellness",
    "Beauty & Personal Care",
    "Fitness",
    "Retail",
    "Automotive",
    "Home Services",
    "Education",
    "Professional & Other",
    "Repair",
    "Other",
]


def flat_choices() -> list[tuple[str, str]]:
    """Flat [(key, label), …] list — for Business.TYPE_CHOICES."""
    return [(key, entry["label"]) for key, entry in TYPE_REGISTRY.items()]


def grouped_choices() -> list[tuple[str, list[tuple[str, str]]]]:
    """Django-compatible optgroup choices [(group_name, [(key, label), …]), …]."""
    by_group: dict[str, list[tuple[str, str]]] = {}
    for key, entry in TYPE_REGISTRY.items():
        by_group.setdefault(entry["group"], []).append((key, entry["label"]))
    return [(g, by_group[g]) for g in GROUP_ORDER if g in by_group]


def get_type(type_key: str) -> dict:
    """Return registry entry for a key, falling back to 'other' for unknown values."""
    return TYPE_REGISTRY.get(type_key) or TYPE_REGISTRY["other"]


def default_categories_for(type_key: str) -> list[dict]:
    """List of {key, label} dicts — the default category chips for that type."""
    return get_type(type_key)["default_categories"]


def default_categories_map(type_key: str) -> dict[str, bool]:
    """Map {category_key: True} suitable for BusinessSettings.categories_enabled."""
    return {c["key"]: True for c in default_categories_for(type_key)}


def category_labels_for(type_key: str) -> dict[str, str]:
    """Map {category_key: human label} used by the customer view to render chips."""
    return {c["key"]: c["label"] for c in default_categories_for(type_key)}


def prompt_hints_for(type_key: str) -> tuple[str, str]:
    """Return (vocabulary_hints, style_hints) to inject into the AI prompt."""
    entry = get_type(type_key)
    return entry.get("vocabulary_hints", ""), entry.get("style_hints", "")
