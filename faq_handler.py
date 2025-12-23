"""
FAQ Handler Module
Handles FAQ categories, knowledge base lookups, and RAG for free-form questions
"""

from typing import Optional, List, Dict, Any, Tuple
from config import get_settings
import re

settings = get_settings()

# Try to import OpenAI for RAG (optional)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = settings.openai_api_key != ""
except ImportError:
    OPENAI_AVAILABLE = False


# ============================================
# FAQ CATEGORIES (Static for WhatsApp menu)
# ============================================

FAQ_CATEGORIES = [
    {"id": "faq_dates", "title": "📅 Dates & Schedule", "category": "dates_schedule"},
    {"id": "faq_fares", "title": "💰 Fares", "category": "fares"},
    {"id": "faq_route", "title": "🗺️ Route Info", "category": "route"},
    {"id": "faq_return", "title": "🔄 Return Service", "category": "return_service"},
    {"id": "faq_luggage", "title": "🧳 Luggage Policy", "category": "luggage"},
    {"id": "faq_locations", "title": "📍 Pickup/Drop Points", "category": "locations"},
    {"id": "faq_seats", "title": "💺 Seats Availability", "category": "seats"},
    {"id": "faq_general", "title": "❓ General", "category": "general"},
]


# ============================================
# DETERMINISTIC FAQ RESPONSES
# ============================================

def get_faq_response_by_category(category: str, supabase_client) -> str:
    """
    Get deterministic FAQ response for a category.
    Pulls from business_settings and knowledge_base tables.
    """
    
    if category == "dates_schedule":
        return get_dates_schedule_response(supabase_client)
    
    elif category == "fares":
        return get_fares_response(supabase_client)
    
    elif category == "route":
        return get_route_response(supabase_client)
    
    elif category == "return_service":
        return get_return_service_response(supabase_client)
    
    elif category == "luggage":
        return get_luggage_response(supabase_client)
    
    elif category == "locations":
        return get_locations_response(supabase_client)
    
    elif category == "seats":
        return get_seats_response(supabase_client)
    
    elif category == "general":
        return get_general_response(supabase_client)
    
    else:
        return "Sorry, I couldn't find information for that category. Please try another option."


def get_dates_schedule_response(supabase) -> str:
    """Get dates and schedule info from settings"""
    try:
        outbound = supabase.table("business_settings").select("setting_value").eq("setting_key", "outbound_dates").single().execute()
        return_info = supabase.table("business_settings").select("setting_value").eq("setting_key", "return_service").single().execute()
        schedule = supabase.table("business_settings").select("setting_value").eq("setting_key", "service_schedule").single().execute()
        
        outbound_data = outbound.data["setting_value"] if outbound.data else {}
        return_data = return_info.data["setting_value"] if return_info.data else {}
        schedule_data = schedule.data["setting_value"] if schedule.data else {}
        
        response = """📅 *Dates & Schedule*

*Outbound Service:*
""" + outbound_data.get("description", "Dates TBD") + """

*Return Service:*
""" + return_data.get("description", "Return dates TBD") + """

*Regular Schedule:*
""" + schedule_data.get("normal_schedule", "During semester breaks") + """

ℹ️ """ + schedule_data.get("note", "Schedule may change if required")
        
        return response
    except Exception as e:
        print(f"Error getting dates: {e}")
        return "📅 *Dates & Schedule*\n\nOutbound: Saturday 3rd & Sunday 4th January 2026\nReturn: Sunday 18th January 2026"


def get_fares_response(supabase) -> str:
    """Get fare information from settings"""
    try:
        fares = supabase.table("business_settings").select("setting_value").eq("setting_key", "fares").single().execute()
        fares_data = fares.data["setting_value"] if fares.data else {}
        
        multan_fare = fares_data.get("multan", 3500)
        bahawalpur_fare = fares_data.get("bahawalpur", 4200)
        
        response = f"""💰 *Ticket Fares*

🏙️ *GIKI → Multan:* Rs. {multan_fare:,}
🏙️ *GIKI → Bahawalpur:* Rs. {bahawalpur_fare:,}

📝 *Note:* Bahawalpur fare is higher as the bus continues from Multan to Bahawalpur after dropping Multan passengers.

💳 Payment via bank transfer after booking."""
        
        return response
    except Exception as e:
        print(f"Error getting fares: {e}")
        return "💰 *Fares*\n\nMultan: Rs. 3,500\nBahawalpur: Rs. 4,200"


def get_route_response(supabase) -> str:
    """Get route information from settings"""
    try:
        route = supabase.table("business_settings").select("setting_value").eq("setting_key", "route_info").single().execute()
        route_data = route.data["setting_value"] if route.data else {}
        
        response = """🗺️ *Route Information*

*Service:* """ + route_data.get("description", "Bus service for GIKI students") + """

*Destinations:*
1️⃣ Multan (First Stop)
2️⃣ Bahawalpur (Final Stop)

📝 Both destinations use the same bus. Multan students are dropped first, then the bus continues to Bahawalpur."""
        
        return response
    except Exception as e:
        print(f"Error getting route: {e}")
        return "🗺️ *Route*\n\nGIKI → Multan → Bahawalpur\n\nSame bus for both destinations."


def get_return_service_response(supabase) -> str:
    """Get return service information"""
    try:
        return_info = supabase.table("business_settings").select("setting_value").eq("setting_key", "return_service").single().execute()
        return_data = return_info.data["setting_value"] if return_info.data else {}
        
        response = """🔄 *Return Service*

*Return Date:* """ + return_data.get("description", "Sunday 18th January 2026") + """

*Pickup Points:*
• Bahawalpur → GIKI
• Multan → GIKI

📝 Same pricing applies for return journey.
Book your return ticket through the booking menu!"""
        
        return response
    except Exception as e:
        print(f"Error getting return info: {e}")
        return "🔄 *Return Service*\n\nReturn to GIKI: Sunday 18th January 2026\nAvailable from both Multan and Bahawalpur."


def get_luggage_response(supabase) -> str:
    """Get luggage policy from settings"""
    try:
        luggage = supabase.table("business_settings").select("setting_value").eq("setting_key", "luggage_policy").single().execute()
        luggage_data = luggage.data["setting_value"] if luggage.data else {}
        
        max_bags = luggage_data.get("max_bags", 2)
        bag_size = luggage_data.get("bag_size", "medium")
        
        response = f"""🧳 *Luggage Policy*

*Allowed:*
• {max_bags} {bag_size}-sized bags maximum
• 1 hand carry bag

*Extra Luggage:*
• No extra charges! ✅
• However, large amounts of luggage may need to be adjusted with your seat due to storage constraints.

⚠️ *Recommendation:*
Please pack light. Only bring what you need to ensure comfortable travel for everyone."""
        
        return response
    except Exception as e:
        print(f"Error getting luggage: {e}")
        return "🧳 *Luggage*\n\n2 medium bags + 1 hand carry\nNo extra charge, but excess may go with your seat."


def get_locations_response(supabase) -> str:
    """Get pickup/drop locations from settings"""
    try:
        locations = supabase.table("business_settings").select("setting_value").eq("setting_key", "pickup_locations").single().execute()
        loc_data = locations.data["setting_value"] if locations.data else {}
        
        status = loc_data.get("status", "TBD")
        note = loc_data.get("note", "Locations will be shared soon")
        location_list = loc_data.get("locations", [])
        
        if status == "TBD" or not location_list:
            response = """📍 *Pickup & Drop Locations*

⏳ *Status:* To Be Announced

""" + note + """

Stay tuned! We'll update you once locations are finalized.

💡 Tip: Check back closer to travel date for exact locations."""
        else:
            response = """📍 *Pickup & Drop Locations*

"""
            for loc in location_list:
                response += f"📌 {loc}\n"
        
        return response
    except Exception as e:
        print(f"Error getting locations: {e}")
        return "📍 *Locations*\n\nExact locations will be shared closer to travel date."


def get_seats_response(supabase) -> str:
    """Get real-time seats availability from database"""
    try:
        # Get available dates with bus info
        dates = supabase.table("available_dates").select("*, buses(*)").gte("date", "2024-01-01").order("date").execute()
        
        if not dates.data:
            return "💺 *Seats Availability*\n\nNo upcoming trips scheduled. Check back later!"
        
        response = "💺 *Seats Availability*\n\n"
        
        for date_info in dates.data:
            bus = date_info.get("buses", {})
            route = date_info.get("route", "Unknown")
            travel_date = date_info.get("date", "")
            seats_available = date_info.get("seats_available", 0)
            total_seats = bus.get("total_seats", 0)
            
            # Calculate percentage
            if total_seats > 0:
                pct = (seats_available / total_seats) * 100
                if pct > 50:
                    status_emoji = "🟢"
                elif pct > 20:
                    status_emoji = "🟡"
                else:
                    status_emoji = "🔴"
            else:
                status_emoji = "⚪"
            
            response += f"{status_emoji} *{route}* - {travel_date}\n"
            response += f"   {seats_available}/{total_seats} seats available\n\n"
        
        response += "🟢 Good | 🟡 Filling up | 🔴 Almost full"
        
        return response
    except Exception as e:
        print(f"Error getting seats: {e}")
        return "💺 *Seats*\n\nUnable to fetch availability. Please try booking to see options."


def get_general_response(supabase) -> str:
    """Get general FAQ information"""
    return """❓ *General Information*

*What is Safar-e-GIKI?*
A bus service exclusively for GIKI students traveling to/from campus.

*How to Book?*
1️⃣ Tap "Book a Seat" from main menu
2️⃣ Select route & date
3️⃣ Enter your details
4️⃣ Choose your seat
5️⃣ Complete payment

*How to Check Booking?*
Go to Status → Your Booking → Enter phone number

*Need Help?*
Type your question and our system will find the answer!

*Contact:*
Message us anytime through this chat."""


# ============================================
# RAG SEARCH FOR FREE-FORM QUESTIONS
# ============================================

def extract_keywords(text: str) -> List[str]:
    """Extract keywords from user query for KB search"""
    # Common keywords to look for
    keyword_map = {
        "date": ["date", "when", "time", "schedule", "day", "january", "saturday", "sunday"],
        "fare": ["fare", "price", "cost", "ticket", "pay", "money", "rupee", "pkr", "rs"],
        "route": ["route", "where", "destination", "city", "multan", "bahawalpur", "giki", "stop"],
        "return": ["return", "back", "coming", "reverse"],
        "luggage": ["luggage", "bag", "baggage", "carry", "weight", "heavy", "suitcase"],
        "location": ["location", "pickup", "drop", "point", "station", "bus stop", "where"],
        "seat": ["seat", "available", "book", "reserve", "left", "remaining"],
        "general": ["book", "how", "what", "who", "help", "student"]
    }
    
    text_lower = text.lower()
    found_keywords = []
    
    for category, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text_lower:
                found_keywords.append(kw)
    
    return list(set(found_keywords))


def search_knowledge_base(query: str, supabase_client) -> Optional[str]:
    """
    Search knowledge base for matching FAQ entries.
    Uses keyword matching (no embeddings required).
    """
    keywords = extract_keywords(query)
    
    if not keywords:
        return None
    
    try:
        # Search by keywords overlap
        results = supabase_client.table("knowledge_base").select("*").eq("is_active", True).execute()
        
        if not results.data:
            return None
        
        # Score each result by keyword match
        scored_results = []
        for entry in results.data:
            entry_keywords = entry.get("keywords", [])
            score = len(set(keywords) & set(entry_keywords))
            if score > 0:
                scored_results.append((score, entry))
        
        # Sort by score and get top result
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        if scored_results:
            best_match = scored_results[0][1]
            return best_match.get("answer", None)
        
        return None
    except Exception as e:
        print(f"KB search error: {e}")
        return None


async def handle_faq_question(query: str, supabase_client) -> str:
    """
    Handle a free-form FAQ question.
    First tries keyword search, then falls back to general response.
    """
    # Try keyword-based search first
    kb_answer = search_knowledge_base(query, supabase_client)
    
    if kb_answer:
        return f"💡 *Answer:*\n\n{kb_answer}\n\n_Need more help? Select a category or ask another question._"
    
    # Check for specific keywords to provide targeted responses
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["price", "fare", "cost", "ticket"]):
        return get_fares_response(supabase_client)
    
    elif any(word in query_lower for word in ["date", "when", "schedule"]):
        return get_dates_schedule_response(supabase_client)
    
    elif any(word in query_lower for word in ["luggage", "bag", "baggage"]):
        return get_luggage_response(supabase_client)
    
    elif any(word in query_lower for word in ["seat", "available", "left"]):
        return get_seats_response(supabase_client)
    
    elif any(word in query_lower for word in ["return", "back"]):
        return get_return_service_response(supabase_client)
    
    elif any(word in query_lower for word in ["route", "multan", "bahawalpur"]):
        return get_route_response(supabase_client)
    
    elif any(word in query_lower for word in ["location", "pickup", "drop", "where"]):
        return get_locations_response(supabase_client)
    
    # Default response
    return """🤔 I couldn't find a specific answer to your question.

Please try:
1️⃣ Selecting a category from the FAQ menu
2️⃣ Rephrasing your question
3️⃣ Using keywords like: fare, date, route, luggage, seat

Or type 'menu' to go back to main menu."""


# ============================================
# RAG WITH OPENAI (Optional Enhancement)
# ============================================

async def rag_search_with_ai(query: str, supabase_client) -> Optional[str]:
    """
    Enhanced RAG search using OpenAI embeddings.
    Only used if OpenAI is configured.
    """
    if not OPENAI_AVAILABLE:
        return None
    
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        
        # Get all KB entries
        kb_entries = supabase_client.table("knowledge_base").select("question, answer, category").eq("is_active", True).execute()
        
        if not kb_entries.data:
            return None
        
        # Build context from KB
        context = "\n\n".join([
            f"Q: {entry['question']}\nA: {entry['answer']}"
            for entry in kb_entries.data
        ])
        
        # Get business settings for live data
        settings_data = supabase_client.table("business_settings").select("*").execute()
        settings_context = "\n".join([
            f"{s['setting_key']}: {s['setting_value']}"
            for s in settings_data.data
        ]) if settings_data.data else ""
        
        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a helpful FAQ assistant for Safar-e-GIKI bus service.
Answer questions based ONLY on the following knowledge base and settings.
Keep answers concise and WhatsApp-friendly.

KNOWLEDGE BASE:
{context}

CURRENT SETTINGS:
{settings_context}

If you cannot find the answer, say so politely."""
                },
                {"role": "user", "content": query}
            ],
            max_tokens=300,
            temperature=0.3
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI RAG error: {e}")
        return None