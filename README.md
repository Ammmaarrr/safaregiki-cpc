# 🚌 Safar-e-GIKI WhatsApp Bot

A comprehensive WhatsApp bot backend for GIKI student bus booking system with FAQ categories, RAG-powered Q&A, and admin dashboard.

## Features

### User Features
- **Book a Seat**: Complete booking flow - Route → Date → Passenger Details → Seat → Payment
- **Status Check**: View bus status and lookup personal bookings by phone
- **FAQ System**: 8 category-based FAQ with deterministic responses + free-form question support
- **Payment Upload**: Web-based screenshot upload for payment verification

### Admin Features (WhatsApp + Web Dashboard)
- **Edit Fares**: Update Multan/Bahawalpur ticket prices
- **Edit Dates**: Modify outbound travel dates
- **Edit Return Service**: Update return journey details
- **Edit Luggage Policy**: Change baggage rules
- **Edit Locations**: Set pickup/drop points
- **View Seats**: Real-time seat availability overview
- **Rebuild KB**: Update FAQ responses with latest settings
- **Audit Log**: Track last 10 admin changes

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **Messaging**: Meta WhatsApp Business API
- **RAG**: Keyword-based search + Optional OpenAI integration
- **Deployment**: Docker-ready

## Project Structure

```
whatsapp-bot/
├── main.py                 # FastAPI app, webhooks, admin API
├── config.py               # Environment configuration
├── database.py             # Supabase database operations
├── whatsapp_client.py      # WhatsApp API client & messages
├── message_handler.py      # Message processing & routing
├── session_manager.py      # User session & state management
├── faq_handler.py          # FAQ categories & RAG search
├── admin_handler.py        # Admin authentication & actions
├── schema_update.sql       # Database schema for new tables
├── templates/
│   └── admin_dashboard.html # Web-based admin panel
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- Meta Business Account with WhatsApp Business API
- Supabase project

### 2. Database Setup

Run the SQL files in your Supabase SQL editor in order:
1. Original schema (buses, available_dates, bookings)
2. `schema_update.sql` (business_settings, knowledge_base, faq_categories, admin_audit_log)

### 3. Environment Configuration

```bash
cp .env.example .env
```

Fill in your credentials:

```env
# Meta WhatsApp API
META_ACCESS_TOKEN=your_token
PHONE_NUMBER_ID=your_phone_id
VERIFY_TOKEN=your_verify_token

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key

# OpenAI (optional for enhanced RAG)
OPENAI_API_KEY=your_openai_key

# App
APP_URL=https://your-domain.com

# Admin - comma-separated phone numbers
ADMIN_PHONE_NUMBERS=923001234567,923009876543
ADMIN_SECRET_KEY=your-secret-key
```

### 4. Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or with Docker:

```bash
docker-compose up --build
```

### 5. Configure Meta Webhook

1. Go to Meta Developer Console → Your App → WhatsApp → Configuration
2. Set Webhook URL: `https://your-domain.com/webhook`
3. Set Verify Token: Same as `VERIFY_TOKEN` in `.env`
4. Subscribe to: `messages`

## FAQ System

### Categories (Deterministic Responses)
When user taps a category, they get pre-defined responses pulled from database:

| Category | Content |
|----------|---------|
| 📅 Dates & Schedule | Outbound dates, return date, schedule info |
| 💰 Fares | Multan Rs.3,500, Bahawalpur Rs.4,200 |
| 🗺️ Route Info | GIKI → Multan → Bahawalpur journey |
| 🔄 Return Service | Sunday 18th Jan 2026 |
| 🧳 Luggage Policy | 2 medium bags + hand carry |
| 📍 Pickup/Drop Points | TBD / confirmed locations |
| 💺 Seats Availability | Real-time from database |
| ❓ General | Booking help, contact info |

### Free-Form Questions (RAG)
When user types a question, the bot:
1. Extracts keywords from query
2. Searches knowledge_base table by keyword overlap
3. Returns best matching answer
4. Falls back to category detection if no match

## Admin Access

### WhatsApp Admin
Admins can type "admin" or "/admin" to access:
- View/edit all settings via text commands
- Example: `fare multan 3800` updates Multan fare

### Web Dashboard
Access at `https://your-domain.com/admin`:
- Visual interface for all settings
- Real-time seats overview
- One-click KB rebuild
- Audit log viewer

## API Endpoints

### Public Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/webhook` | Meta verification |
| POST | `/webhook` | WhatsApp messages |
| GET | `/upload/{booking_id}` | Payment upload page |
| GET | `/api/buses` | List active buses |
| GET | `/api/dates/{route}` | Available dates |
| GET | `/api/bookings/{phone}` | User bookings |

### Admin Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin` | Admin dashboard |
| POST | `/admin/login` | Admin authentication |
| GET | `/admin/settings/{key}` | Get setting |
| POST | `/admin/settings/fares` | Update fares |
| POST | `/admin/settings/dates` | Update dates |
| POST | `/admin/settings/return` | Update return |
| POST | `/admin/settings/luggage` | Update luggage |
| POST | `/admin/settings/locations` | Update locations |
| GET | `/admin/seats` | Seats overview |
| POST | `/admin/rebuild-kb` | Rebuild KB |
| GET | `/admin/audit-log` | View audit log |

## Business Information

- **Service**: Bus transport for GIKI students
- **Destinations**: Multan (Rs.3,500), Bahawalpur (Rs.4,200)
- **Outbound Dates**: Sat 3rd Jan & Sun 4th Jan 2026
- **Return Date**: Sun 18th Jan 2026
- **Route**: Same bus - GIKI → Multan → Bahawalpur
- **Luggage**: 2 medium bags + hand carry, no extra charge
- **Locations**: TBD (to be announced)
- **Schedule**: Normally during mid/semester breaks

## Conversation Flow

```
Welcome to Safar-e-GIKI!
├── 🎫 Book a Seat
│   ├── Select Route (Multan/Bahawalpur)
│   ├── Select Date
│   ├── Enter Name
│   ├── Enter Reg Number (202XXXX)
│   ├── Enter Phone (03XXXXXXXXX)
│   ├── Select Seat
│   ├── Confirm Booking
│   └── Payment Info + Upload Link
│
├── 📊 Status
│   ├── 🚌 Bus Status
│   └── 🎫 Your Booking (lookup by phone)
│
└── ❓ FAQ
    ├── 📅 Dates & Schedule
    ├── 💰 Fares
    ├── 🗺️ Route Info
    ├── 🔄 Return Service
    ├── 🧳 Luggage Policy
    ├── 📍 Pickup/Drop Points
    ├── 💺 Seats Availability
    └── ❓ General Questions
```

## License

MIT License