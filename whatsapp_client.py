import httpx
from typing import Optional, List, Dict, Any
from config import get_settings

settings = get_settings()

WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{settings.phone_number_id}/messages"


async def send_whatsapp_message(
    to: str,
    message_type: str,
    content: Dict[str, Any]
) -> bool:
    """Send a message via WhatsApp API"""
    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        **content
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                WHATSAPP_API_URL,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending WhatsApp message: {e}")
            return False


async def send_text_message(to: str, text: str) -> bool:
    """Send a simple text message"""
    content = {
        "type": "text",
        "text": {"body": text}
    }
    return await send_whatsapp_message(to, "text", content)


async def send_image_message(to: str, image_url: str, caption: str = "") -> bool:
    """Send an image message"""
    content = {
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption
        }
    }
    return await send_whatsapp_message(to, "image", content)


async def send_button_message(
    to: str,
    body_text: str,
    buttons: List[Dict[str, str]],
    header: Optional[str] = None,
    footer: Optional[str] = None
) -> bool:
    """Send an interactive button message (max 3 buttons)"""
    interactive = {
        "type": "button",
        "body": {"text": body_text},
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {
                        "id": btn["id"],
                        "title": btn["title"][:20]  # Max 20 chars
                    }
                }
                for btn in buttons[:3]  # Max 3 buttons
            ]
        }
    }
    
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
    
    content = {
        "type": "interactive",
        "interactive": interactive
    }
    return await send_whatsapp_message(to, "interactive", content)


async def send_list_message(
    to: str,
    body_text: str,
    button_text: str,
    sections: List[Dict[str, Any]],
    header: Optional[str] = None,
    footer: Optional[str] = None
) -> bool:
    """Send an interactive list message"""
    interactive = {
        "type": "list",
        "body": {"text": body_text},
        "action": {
            "button": button_text[:20],
            "sections": sections
        }
    }
    
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
    
    content = {
        "type": "interactive",
        "interactive": interactive
    }
    return await send_whatsapp_message(to, "interactive", content)


# ============== PRE-BUILT MESSAGE TEMPLATES ==============

async def send_welcome_message(to: str, welcome_image_url: Optional[str] = None) -> bool:
    """Send welcome message with main menu"""
    welcome_text = """🚌 *Welcome to Safar-e-GIKI!* 🚌

Your trusted travel partner for comfortable journeys between GIKI and Multan.

How can we help you today?"""
    
    # Send welcome image if provided
    if welcome_image_url:
        await send_image_message(to, welcome_image_url, "Welcome to Safar-e-GIKI!")
    
    buttons = [
        {"id": "book_seat", "title": "🎫 Book a Seat"},
        {"id": "status", "title": "📊 Status"},
        {"id": "faq", "title": "❓ FAQ"}
    ]
    
    return await send_button_message(
        to,
        welcome_text,
        buttons,
        footer="Safe travels with Safar-e-GIKI"
    )


async def send_main_menu(to: str) -> bool:
    """Send main menu buttons"""
    text = "What would you like to do?"
    
    buttons = [
        {"id": "book_seat", "title": "🎫 Book a Seat"},
        {"id": "status", "title": "📊 Status"},
        {"id": "faq", "title": "❓ FAQ"}
    ]
    
    return await send_button_message(to, text, buttons)


async def send_destination_selection(to: str) -> bool:
    """Send destination selection buttons"""
    text = "🗺️ *Select Your Route*\n\nWhere would you like to travel?"
    
    buttons = [
        {"id": "route_giki_multan", "title": "GIKI → Multan"},
        {"id": "route_multan_giki", "title": "Multan → GIKI"},
        {"id": "main_menu", "title": "🔙 Main Menu"}
    ]
    
    return await send_button_message(to, text, buttons)


async def send_status_menu(to: str) -> bool:
    """Send status menu buttons"""
    text = "📊 *Status Menu*\n\nWhat would you like to check?"
    
    buttons = [
        {"id": "bus_status", "title": "🚌 Bus Status"},
        {"id": "your_booking", "title": "🎫 Your Booking"},
        {"id": "main_menu", "title": "🔙 Main Menu"}
    ]
    
    return await send_button_message(to, text, buttons)


async def send_faq_message(to: str) -> bool:
    """Send FAQ information"""
    faq_text = """❓ *Frequently Asked Questions*

*Q: What routes are available?*
A: We operate between GIKI and Multan.

*Q: What bus types do you offer?*
A: Business (27 seats), Executive (49 seats), and Sleeper (34 seats).

*Q: How do I pay?*
A: Currently via bank transfer. Upload your payment screenshot after booking.

*Q: How do I check my booking?*
A: Click 'Status' → 'Your Booking' and enter your phone number.

*Q: Can I cancel my booking?*
A: Contact our support for cancellation requests.

*Q: What amenities are included?*
A: AC, charging ports, and refreshments. Executive adds WiFi & extra legroom. Sleeper includes berths & blankets.

*Q: What ID format is required?*
A: Student ID: 202XXXX format
   Phone: 03XXXXXXXXX format"""
    
    await send_text_message(to, faq_text)
    
    buttons = [{"id": "main_menu", "title": "🔙 Main Menu"}]
    return await send_button_message(to, "Need anything else?", buttons)


async def send_payment_info(to: str, booking_id: str, amount: int) -> bool:
    """Send payment information"""
    payment_text = f"""💳 *Payment Information*

*Booking ID:* {booking_id}
*Amount Due:* Rs. {amount:,}

━━━━━━━━━━━━━━━━━━━━━

*Bank Transfer Details:*

🏦 *Bank Name:* HBL (Habib Bank Limited)
📋 *Account Title:* Safar-e-GIKI Transport
🔢 *Account Number:* 1234-5678-9012-3456
📍 *Branch Code:* 0001

━━━━━━━━━━━━━━━━━━━━━

*Alternative - JazzCash/EasyPaisa:*
📱 *Number:* 0300-1234567
👤 *Name:* Safar-e-GIKI

━━━━━━━━━━━━━━━━━━━━━

⚠️ *Important:* 
1. Use your Booking ID ({booking_id}) as payment reference
2. After payment, upload screenshot to confirm your seat"""
    
    await send_text_message(to, payment_text)
    
    buttons = [
        {"id": f"upload_screenshot_{booking_id}", "title": "📤 Upload Screenshot"},
        {"id": "main_menu", "title": "🔙 Main Menu"}
    ]
    
    return await send_button_message(
        to,
        "Click below to upload your payment screenshot:",
        buttons
    )


async def send_screenshot_upload_link(to: str, booking_id: str) -> bool:
    """Send link to upload payment screenshot"""
    # Placeholder URL - replace with your actual upload endpoint
    upload_url = f"{settings.app_url}/upload/{booking_id}"
    
    text = f"""📤 *Upload Payment Screenshot*

Please upload your payment screenshot using the link below:

🔗 {upload_url}

Your Booking ID: *{booking_id}*

After uploading, your booking will be verified within 24 hours.

Thank you for choosing Safar-e-GIKI! 🚌"""
    
    await send_text_message(to, text)
    
    buttons = [{"id": "main_menu", "title": "🔙 Main Menu"}]
    return await send_button_message(to, "Need anything else?", buttons)


# ============== FAQ MENU ==============

async def send_faq_categories_menu(to: str) -> bool:
    """Send FAQ categories as a list menu"""
    body_text = """❓ *FAQ - Frequently Asked Questions*

Select a category to learn more, or type your question directly!"""
    
    sections = [{
        "title": "FAQ Categories",
        "rows": [
            {"id": "faq_dates", "title": "📅 Dates & Schedule", "description": "Travel dates and timings"},
            {"id": "faq_fares", "title": "💰 Fares", "description": "Ticket prices for all routes"},
            {"id": "faq_route", "title": "🗺️ Route Info", "description": "Destinations and stops"},
            {"id": "faq_return", "title": "🔄 Return Service", "description": "Return journey details"},
            {"id": "faq_luggage", "title": "🧳 Luggage Policy", "description": "Baggage rules and limits"},
            {"id": "faq_locations", "title": "📍 Pickup/Drop Points", "description": "Bus stop locations"},
            {"id": "faq_seats", "title": "💺 Seats Availability", "description": "Check available seats"},
            {"id": "faq_general", "title": "❓ General", "description": "Booking help and more"},
        ]
    }]
    
    return await send_list_message(
        to,
        body_text,
        "Select Category",
        sections,
        footer="Or type your question to search"
    )


async def send_faq_response_with_menu(to: str, response_text: str) -> bool:
    """Send FAQ response with back to menu option"""
    await send_text_message(to, response_text)
    
    buttons = [
        {"id": "faq", "title": "📋 More FAQ"},
        {"id": "book_seat", "title": "🎫 Book Now"},
        {"id": "main_menu", "title": "🔙 Main Menu"}
    ]
    
    return await send_button_message(
        to,
        "What would you like to do next?",
        buttons
    )


# ============== ADMIN MENU ==============

async def send_admin_menu(to: str) -> bool:
    """Send admin dashboard menu"""
    body_text = """🔐 *ADMIN DASHBOARD*
━━━━━━━━━━━━━━━━━━━━━

Welcome, Administrator!
Select an option to manage Safar-e-GIKI:"""
    
    sections = [{
        "title": "Admin Options",
        "rows": [
            {"id": "admin_fares", "title": "💰 Edit Fares", "description": "Update ticket prices"},
            {"id": "admin_dates", "title": "📅 Edit Dates", "description": "Modify travel dates"},
            {"id": "admin_return", "title": "🔄 Edit Return", "description": "Update return service"},
            {"id": "admin_luggage", "title": "🧳 Edit Luggage", "description": "Change luggage policy"},
            {"id": "admin_locations", "title": "📍 Edit Locations", "description": "Set pickup/drop points"},
            {"id": "admin_seats", "title": "💺 View Seats", "description": "Check seat availability"},
            {"id": "admin_rebuild_kb", "title": "🔄 Rebuild KB", "description": "Update FAQ database"},
            {"id": "admin_audit_log", "title": "📋 Audit Log", "description": "View recent changes"},
        ]
    }]
    
    return await send_list_message(
        to,
        body_text,
        "Select Option",
        sections,
        footer="Admin access only"
    )


async def send_admin_response(to: str, response_text: str) -> bool:
    """Send admin response with back to admin menu option"""
    await send_text_message(to, response_text)
    
    buttons = [
        {"id": "admin_menu", "title": "🔐 Admin Menu"},
        {"id": "main_menu", "title": "🔙 Main Menu"}
    ]
    
    return await send_button_message(
        to,
        "What would you like to do next?",
        buttons
    )