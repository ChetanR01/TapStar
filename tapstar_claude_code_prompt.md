# Tapstar — Claude Code Project Prompt
# AI-Powered Google Review SaaS Platform

---

## CONTEXT & REFERENCE

I am attaching a PDF (`TapStar_Product_Spec.pdf`) that contains the complete product specification for Tapstar. Read it fully before writing any code. It covers all features, user flows, pricing tiers, and the GTM strategy. Use it as the single source of truth for product decisions.

---

## WHAT YOU ARE BUILDING

**Tapstar** is a B2B SaaS platform that helps Indian local businesses (restaurants, salons, clinics, retail shops) collect more genuine Google reviews through an AI-powered QR code experience.

**Core flow:**
1. Business registers on Tapstar → gets a unique QR code
2. Customer scans QR at the counter/table → lands on a mobile review page (no login, no app)
3. Customer picks star rating + categories + specific items
4. AI generates 4 review variants in different Indian language styles (Hinglish, Minglish, Hindi, English)
5. 1–2 star ratings → redirect to private feedback form (never reaches Google)
6. 4–5 star ratings → opens Google Review page with text pre-filled
7. Customer taps Submit on Google. Done.

---

## TECH STACK

- **Backend:** Django 5.x + Django REST Framework
- **Database:** PostgreSQL
- **AI:** Anthropic API (`claude-sonnet-4-20250514`) for review generation
- **QR generation:** `qrcode` + `Pillow` Python libraries
- **PDF generation:** `ReportLab` (for printable QR standee)
- **Payments:** Razorpay (UPI + cards + net banking, INR)
- **Task queue:** Celery + Redis (async AI calls, PDF generation, email digests)
- **Business dashboard:** Django templates + HTMX (server-rendered, minimal JS)
- **Customer QR page:** Pure HTML + Vanilla JS (must be extremely lightweight — fast load on 4G)
- **Hosting-ready:** Must work on Railway / Render with environment variable config

---

## DJANGO APP STRUCTURE

Create exactly these 6 Django apps:

```
tapstar/
├── accounts/        # Auth, subscription status, Razorpay billing hooks
├── businesses/      # Business profile, locations, Google Place ID, QR records
├── reviews/         # AI generation, variant storage, submission tracking
├── feedback/        # Negative review private inbox, feedback form submissions
├── analytics/       # Dashboard stats, trends, language/category breakdowns
└── settings_mgr/    # Per-business language, tone, keywords, categories, blocked phrases
```

---

## DATABASE MODELS

Design models carefully. Key relationships:

### accounts app
```
User
- email, password (Django auth)
- subscription_plan: CharField (starter/growth/business)
- subscription_status: CharField (trial/active/expired/cancelled)
- trial_ends_at: DateTimeField
- razorpay_customer_id: CharField
- razorpay_subscription_id: CharField
- created_at, updated_at
```

### businesses app
```
Business
- owner: FK(User)
- name: CharField
- business_type: CharField (restaurant/salon/clinic/retail/other)
- google_place_id: CharField
- google_review_url: CharField  # constructed from place_id
- address: TextField
- logo: ImageField (optional)
- is_active: BooleanField
- created_at

Location
- business: FK(Business)
- name: CharField  # e.g. "Andheri Branch"
- google_place_id: CharField  # can differ per branch
- google_review_url: CharField
- qr_code_token: UUIDField(unique=True)  # used in QR URL
- qr_code_image: ImageField
- is_active: BooleanField
- created_at
```

### settings_mgr app
```
BusinessSettings
- business: OneToOneField(Business)
- language_mode: CharField
  choices: ['hinglish','minglish','hindi','marathi','english','random']
  default: 'random'
- tone_mode: CharField
  choices: ['casual','formal','enthusiastic','random']
  default: 'random'
- allow_customer_language_change: BooleanField(default=True)
- review_length: CharField choices: ['short','medium','detailed'] default:'medium'
- mention_business_name: BooleanField(default=True)
- negative_filter_threshold: IntegerField(default=2)  # ratings <= this go to private form
- custom_keywords: ArrayField(CharField) or JSONField  # list of strings
- blocked_phrases: ArrayField(CharField) or JSONField  # list of strings
- categories_enabled: JSONField  # {"food": true, "staff": true, "service": true, "ambiance": true}
- menu_items: JSONField  # list of item names business has configured

LocationSettings
- location: OneToOneField(Location)
- (inherits from BusinessSettings, overrides per-location if set)
- overrides: JSONField  # only stores fields that differ from business-level settings
```

### reviews app
```
ReviewRequest
- location: FK(Location)
- session_token: UUIDField  # anonymous session per customer visit
- star_rating: IntegerField (1-5)
- selected_categories: JSONField  # ["food", "staff"]
- selected_items: JSONField  # ["Butter Chicken", "Garlic Naan"]
- language_mode_used: CharField
- tone_mode_used: CharField
- is_negative: BooleanField  # True if rating <= threshold
- created_at

ReviewVariant
- request: FK(ReviewRequest)
- variant_number: IntegerField (1-4)
- language: CharField  # actual language used for this variant
- tone: CharField  # actual tone used for this variant
- text: TextField
- was_selected: BooleanField(default=False)
- was_submitted: BooleanField(default=False)
- created_at

ReviewSubmission
- variant: FK(ReviewVariant)
- submitted_at: DateTimeField
- user_agent: CharField  # for analytics
```

### feedback app
```
PrivateFeedback
- location: FK(Location)
- star_rating: IntegerField
- feedback_text: TextField
- customer_name: CharField (optional)
- customer_phone: CharField (optional)
- is_read: BooleanField(default=False)
- created_at
```

### analytics app
```
DailyStats
- location: FK(Location)
- date: DateField
- reviews_generated: IntegerField(default=0)
- reviews_submitted: IntegerField(default=0)
- negative_redirects: IntegerField(default=0)
- avg_rating: DecimalField
- language_breakdown: JSONField  # {"hinglish": 5, "english": 3, ...}
- category_breakdown: JSONField  # {"food": 7, "staff": 4, ...}
```

---

## BUILD ORDER — IMPLEMENT IN THIS EXACT SEQUENCE

### Sprint 1: Foundation & QR Core
1. Django project setup with all 6 apps registered
2. PostgreSQL connection configured via environment variables
3. `User` model with subscription fields
4. `Business` and `Location` models
5. `BusinessSettings` model with all config fields
6. Business registration view + form (name, type, Google Place ID)
7. QR code generation on Location save (use `qrcode` lib, store as PNG in media)
8. Business dashboard home — shows business info + QR code download button
9. Admin panel registered for all models

### Sprint 2: Customer Review Page + AI Generation
1. Public URL route: `/r/<qr_code_token>/` — the customer review page
2. Customer page HTML (pure HTML + vanilla JS, NO frameworks, must load in < 2s on 4G)
   - Business name + logo header
   - Star rating tap selector (large, mobile-friendly)
   - Category multi-select chips (shown after rating selected)
   - Item selector (shown after category selected)
   - Language selector (shown only if `allow_customer_language_change=True`)
   - "Generate Review" button
3. AI generation endpoint: `POST /api/generate-review/`
   - Accepts: location token, rating, categories, items, language preference
   - Calls Anthropic API with carefully engineered prompt (see Prompt section below)
   - Returns 4 variants as JSON with language + tone tags per variant
   - Saves `ReviewRequest` + 4 `ReviewVariant` records
4. Display variants as selectable cards on customer page
5. Edit-before-submit: editable textarea pre-filled with selected variant
6. Regenerate button (calls same endpoint again)
7. "Submit on Google" button logic:
   - Constructs Google Review URL with pre-filled text
   - Opens in new tab
   - Marks variant as `was_submitted=True`
8. Copy-to-clipboard fallback if URL scheme fails

### Sprint 3: Negative Review Filter + Feedback Form
1. Rating check on client side: if rating <= `negative_filter_threshold`, show feedback form instead of AI generation
2. Feedback form: optional name, optional phone, free-text feedback, star rating shown
3. `PrivateFeedback` record saved on submission
4. Business dashboard: Feedback Inbox page showing all private feedbacks, mark-as-read toggle
5. Email notification to business owner on new negative feedback (use Django email + SMTP)

### Sprint 4: Payments (Razorpay)
1. Razorpay SDK integration (`razorpay` Python package)
2. Subscription plans defined as constants matching PDF spec:
   - Starter: free forever
   - Growth: Rs.499/month, 1 month free trial
   - Business: Rs.1199/month, 1 month free trial
3. Upgrade page showing plan comparison
4. Razorpay subscription creation on plan selection
5. Webhook endpoint: `POST /payments/webhook/` — handles subscription.activated, subscription.charged, subscription.cancelled
6. Subscription status gating middleware: blocks access to Pro features if subscription expired
7. Trial countdown banner in dashboard header

### Sprint 5: Analytics Dashboard
1. `DailyStats` aggregation — Celery periodic task runs nightly
2. Dashboard analytics page showing:
   - Total reviews generated (all time + this month)
   - Reviews submitted to Google
   - Negative redirects count
   - Average star rating trend (line chart — use Chart.js via CDN)
   - Language breakdown (pie/donut chart)
   - Category breakdown (bar chart)
3. "Since joining" Google review count comparison widget (manual input by business — they update their actual Google count monthly)

### Sprint 6: Language & Tone Settings
1. Settings page in business dashboard
2. All `BusinessSettings` fields editable via form:
   - Language mode dropdown
   - Tone mode dropdown
   - Toggle: allow customer to change language
   - Review length selector
   - Toggle: mention business name
   - Negative filter threshold slider (1, 2, or 3)
   - Custom keywords: tag input (add/remove chips)
   - Blocked phrases: tag input (add/remove chips)
   - Categories: toggle switches
   - Menu items: add/remove list
3. Save confirmation + live preview of what a review might look like

### Sprint 7: Outreach Tools + Multi-location (Business plan)
1. WhatsApp review link generator — pre-built wa.me link with review page URL + message
2. Multi-location: ability to add additional Location records under same Business
3. Per-location QR codes and settings
4. Business plan gate on multi-location access
5. Printable QR standee PDF: `GET /location/<id>/standee.pdf/`
   - Generated with ReportLab
   - A5 size, business logo, QR code, "Scan to review us" text, business name
   - Professional layout, downloadable

---

## AI PROMPT ENGINEERING

This is the most critical part. The prompt must generate reviews that feel genuinely written by real Indian customers.

```python
REVIEW_GENERATION_PROMPT = """
You are generating Google reviews for a {business_type} called "{business_name}".

CUSTOMER INPUT:
- Star rating: {star_rating}/5
- Categories they experienced: {categories}
- Specific items/services: {items}
- Language mode: {language_mode}
- Tone mode: {tone_mode}
- Review length: {length}

LANGUAGE DEFINITIONS:
- hinglish: Mix of Hindi and English in Roman script. Natural code-switching like real Indian customers text. Example: "Bhai ekdum mast tha, staff bhi bahut helpful tha!"
- minglish: Mix of Marathi and English in Roman script. Example: "Chan jevan hota, nakki parayanda yeil!"
- hindi: Pure Hindi in Devanagari script. Formal or informal based on tone.
- marathi: Pure Marathi in Devanagari script.
- english: Natural Indian English — not British/American formal. Indian rhythm and expressions.
- random: Distribute across all 5 styles — no two variants same language.

TONE DEFINITIONS:
- casual: Friendly, bhai-type, feels like a WhatsApp message. Can use emoji sparingly.
- formal: Polite, structured. Suits professional services.
- enthusiastic: Excited, lots of positive energy, exclamation marks.
- random: Vary tone across variants.

{custom_keywords_instruction}
{blocked_phrases_instruction}
{business_name_instruction}

CRITICAL AUTHENTICITY RULES — STRICTLY FOLLOW:
1. Write exactly like a real Indian customer wrote this on their phone
2. Do NOT use corporate marketing language ("exceptional experience", "highly recommend", "five-star service")
3. Each variant must feel genuinely different — different structure, different expressions, not just translation
4. Allow natural minor imperfections — casual punctuation, emoji in casual tone, informal grammar in Hinglish
5. Reference the specific items/categories selected — make review feel personal and specific
6. Keep it {length_description}
7. Never start two variants with the same first word

OUTPUT FORMAT — respond with ONLY this JSON, no explanation, no markdown:
{{
  "variants": [
    {{
      "variant_number": 1,
      "language": "hinglish",
      "tone": "casual",
      "text": "..."
    }},
    {{
      "variant_number": 2,
      "language": "english",
      "tone": "enthusiastic",
      "text": "..."
    }},
    {{
      "variant_number": 3,
      "language": "minglish",
      "tone": "casual",
      "text": "..."
    }},
    {{
      "variant_number": 4,
      "language": "hindi",
      "tone": "formal",
      "text": "..."
    }}
  ]
}}
"""
```

Build a `PromptBuilder` class in `reviews/ai.py` that:
- Takes the `ReviewRequest` object + business settings
- Builds the prompt by filling in all variables
- Handles `custom_keywords_instruction` — if keywords exist: "Naturally include these words/phrases somewhere in the reviews: {keywords}. Do not force them — only if they fit naturally."
- Handles `blocked_phrases_instruction` — if blocked phrases exist: "NEVER use these words or phrases in any variant: {blocked_phrases}"
- Handles `business_name_instruction` — if enabled: "Mention the business name '{name}' naturally in at least 2 of the 4 variants."
- Handles length: short = "1-2 sentences", medium = "3-4 sentences", detailed = "5-7 sentences"
- After receiving response, checks each variant text for blocked phrases and flags/regenerates if found

---

## CUSTOMER PAGE UX REQUIREMENTS

The `/r/<token>/` page is the product's most important page. Requirements:

```
PERFORMANCE:
- Page must load in under 2 seconds on a 4G connection
- Zero npm packages, zero React, zero Vue
- Single HTML file served by Django view
- CSS inlined or in single <style> block
- JS vanilla only, in single <script> block at bottom
- Total page weight < 100KB before QR code image

MOBILE UX:
- Designed mobile-first (320px minimum width)
- Star selector: large tap targets (minimum 44px each star)
- All buttons: minimum 48px height
- Font size minimum 16px to prevent iOS zoom on input focus
- No horizontal scrolling

FLOW STATE MACHINE (implement in vanilla JS):
State 1: RATING — show only star selector
State 2: CATEGORIES — show category chips after star tapped
State 3: ITEMS — show item chips after at least one category selected  
State 4: GENERATING — show loading spinner, call /api/generate-review/
State 5: VARIANTS — show 4 variant cards, edit textarea, submit button
State 6: SUBMITTED — show success screen with Google Maps link

NEGATIVE FLOW (rating <= threshold):
State 2B: FEEDBACK_FORM — show feedback form instead of categories
State 3B: FEEDBACK_SUBMITTED — thank you screen

LANGUAGE SELECTOR:
- Shown as pill chips ONLY if business allows customer to change
- Pre-selected to business default
- Options: English, Hinglish, Marathi-English, Hindi, Marathi, Surprise me
```

---

## URL STRUCTURE

```python
# tapstar/urls.py
urlpatterns = [
    # Public
    path('', views.landing_page, name='landing'),
    path('r/<uuid:token>/', reviews_views.customer_review_page, name='customer_review'),
    
    # Auth
    path('auth/', include('accounts.urls')),
    
    # Business Dashboard (login required)
    path('dashboard/', include('businesses.urls')),
    path('settings/', include('settings_mgr.urls')),
    path('feedback/', include('feedback.urls')),
    path('analytics/', include('analytics.urls')),
    
    # API (used by customer page JS)
    path('api/generate-review/', reviews_views.generate_review_api, name='generate_review'),
    path('api/submit-review/', reviews_views.submit_review_api, name='submit_review'),
    path('api/submit-feedback/', feedback_views.submit_feedback_api, name='submit_feedback'),
    
    # Payments
    path('payments/', include('accounts.payment_urls')),
    
    # Admin
    path('admin/', admin.site.urls),
]
```

---

## ENVIRONMENT VARIABLES

All secrets via environment variables. Create `.env.example`:

```
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost:5432/tapstar
REDIS_URL=redis://localhost:6379/0

ANTHROPIC_API_KEY=your-anthropic-api-key

RAZORPAY_KEY_ID=your-razorpay-key
RAZORPAY_KEY_SECRET=your-razorpay-secret
RAZORPAY_WEBHOOK_SECRET=your-webhook-secret

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

MEDIA_ROOT=/media
ALLOWED_HOSTS=localhost,tapstar.in
```

---

## SUBSCRIPTION GATING RULES

| Feature | Starter | Growth | Business |
|---|---|---|---|
| AI reviews/month | 50 | Unlimited | Unlimited |
| Locations | 1 | 1 | 5 |
| Language modes | English + Hinglish | All 6 | All 6 |
| Negative review filter | No | Yes | Yes |
| Custom keywords | No | Yes | Yes |
| Analytics dashboard | No | Yes | Yes |
| WhatsApp links | No | Yes | Yes |
| Multi-location dashboard | No | No | Yes |
| API access | No | No | Yes |
| Custom branding | No | No | Yes |

Implement as a `SubscriptionGate` mixin for class-based views and a `@require_plan(plan)` decorator for function-based views.

---

## CODE QUALITY REQUIREMENTS

- Every model must have `__str__` method
- Every view must handle errors gracefully — no 500 pages shown to customers
- The customer review page (`/r/<token>/`) must never crash — if AI fails, show pre-written fallback variants
- All API endpoints return consistent JSON: `{"success": true, "data": {...}}` or `{"success": false, "error": "..."}`
- Use Django's `select_related` and `prefetch_related` to avoid N+1 queries
- Celery tasks for: AI generation (async), PDF generation, daily stats aggregation, weekly email digest
- Log all Anthropic API calls with token usage for cost tracking
- Write at least basic tests for: ReviewRequest creation, AI prompt building, negative filter routing, QR generation

---

## WHAT TO BUILD FIRST (YOUR FIRST SESSION)

Focus Sprint 1 completely:

1. `django-admin startproject tapstar_project`
2. Create all 6 apps
3. Install and configure: `djangorestframework`, `psycopg2-binary`, `celery`, `redis`, `qrcode`, `Pillow`, `anthropic`, `razorpay`, `python-dotenv`, `django-htmx`, `whitenoise`
4. Create all models (just models, no views yet)
5. Run migrations
6. Register all models in admin
7. Business registration form + view
8. QR code generation on Location creation (signal or override save())
9. Simple dashboard home page showing business name + QR code image + download link
10. Confirm: scan the QR → lands on `/r/<token>/` → shows "Coming Soon" placeholder

Do NOT move to Sprint 2 until Sprint 1 is fully working end-to-end.

---

## NOTES FOR CLAUDE CODE

- Product name: **Tapstar**
- Target market: Indian local businesses — non-technical owners
- The PDF attached has complete feature list, pricing, GTM — refer to it for any ambiguity
- When in doubt about a feature, build the simpler version first and note it for expansion
- The customer QR page is the #1 priority for quality — it is what the business's customers will see
- Indian Rupee symbol is Rs. in code (avoid Unicode Rs. symbol for font compatibility)
- All amounts stored in paise (smallest unit) in database, displayed as Rs. in UI
- Razorpay amounts are always in paise — Rs.499 = 49900 paise
```
