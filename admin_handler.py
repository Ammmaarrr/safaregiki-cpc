"""
Admin Handler Module
Handles admin authentication and WhatsApp-based admin dashboard
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from config import get_settings

settings = get_settings()


# ============================================
# ADMIN AUTHENTICATION
# ============================================

def is_admin(phone: str) -> bool:
    """Check if phone number is an admin"""
    admin_phones = settings.get_admin_phones()
    # Normalize phone number (remove + and leading zeros)
    normalized = phone.lstrip("+").lstrip("0")
    
    for admin_phone in admin_phones:
        admin_normalized = admin_phone.lstrip("+").lstrip("0")
        if normalized == admin_normalized or normalized.endswith(admin_normalized) or admin_normalized.endswith(normalized):
            return True
    
    return False


# ============================================
# ADMIN MENU
# ============================================

ADMIN_MENU_OPTIONS = [
    {"id": "admin_fares", "title": "💰 Edit Fares"},
    {"id": "admin_dates", "title": "📅 Edit Dates"},
    {"id": "admin_return", "title": "🔄 Edit Return"},
    {"id": "admin_luggage", "title": "🧳 Edit Luggage"},
    {"id": "admin_locations", "title": "📍 Edit Locations"},
    {"id": "admin_seats", "title": "💺 View Seats"},
    {"id": "admin_rebuild_kb", "title": "🔄 Rebuild KB"},
    {"id": "admin_audit_log", "title": "📋 Audit Log"},
]


def get_admin_menu_text() -> str:
    """Get admin dashboard welcome text"""
    return """🔐 *ADMIN DASHBOARD*
━━━━━━━━━━━━━━━━━━━━━

Welcome, Administrator!

Select an option to manage Safar-e-GIKI:

💰 *Fares* - Update ticket prices
📅 *Dates* - Modify travel dates
🔄 *Return* - Edit return service
🧳 *Luggage* - Update luggage policy
📍 *Locations* - Set pickup/drop points
💺 *Seats* - View seat availability
🔄 *Rebuild KB* - Update FAQ database
📋 *Audit Log* - View recent changes"""


# ============================================
# AUDIT LOGGING
# ============================================

def log_admin_action(supabase_client, admin_phone: str, action: str, details: Dict[str, Any]) -> bool:
    """Log an admin action to audit trail"""
    try:
        supabase_client.table("admin_audit_log").insert({
            "admin_phone": admin_phone,
            "action": action,
            "details": details
        }).execute()
        return True
    except Exception as e:
        print(f"Audit log error: {e}")
        return False


def get_audit_log(supabase_client, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent audit log entries"""
    try:
        result = supabase_client.table("admin_audit_log").select("*").order("created_at", desc=True).limit(limit).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching audit log: {e}")
        return []


def format_audit_log(entries: List[Dict[str, Any]]) -> str:
    """Format audit log entries for display"""
    if not entries:
        return "📋 *Audit Log*\n\nNo recent changes recorded."
    
    response = "📋 *Recent Admin Actions*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for entry in entries[:10]:
        timestamp = entry.get("created_at", "")[:16].replace("T", " ")
        action = entry.get("action", "Unknown")
        phone = entry.get("admin_phone", "")[-4:]  # Last 4 digits
        
        response += f"🕐 {timestamp}\n"
        response += f"👤 Admin: ...{phone}\n"
        response += f"📝 {action}\n\n"
    
    return response


# ============================================
# SETTINGS MANAGEMENT
# ============================================

def get_setting(supabase_client, key: str) -> Optional[Dict[str, Any]]:
    """Get a business setting by key"""
    try:
        result = supabase_client.table("business_settings").select("*").eq("setting_key", key).single().execute()
        return result.data if result.data else None
    except Exception as e:
        print(f"Error getting setting {key}: {e}")
        return None


def update_setting(supabase_client, key: str, value: Dict[str, Any], admin_phone: str) -> bool:
    """Update a business setting"""
    try:
        result = supabase_client.table("business_settings").update({
            "setting_value": value,
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": admin_phone
        }).eq("setting_key", key).execute()
        
        # Log the action
        log_admin_action(supabase_client, admin_phone, f"Updated {key}", {"new_value": value})
        
        return len(result.data) > 0
    except Exception as e:
        print(f"Error updating setting {key}: {e}")
        return False


# ============================================
# ADMIN ACTION HANDLERS
# ============================================

def get_current_fares(supabase_client) -> str:
    """Get current fares for editing"""
    setting = get_setting(supabase_client, "fares")
    if not setting:
        return "Error fetching fares."
    
    fares = setting.get("setting_value", {})
    multan = fares.get("multan", 3500)
    bahawalpur = fares.get("bahawalpur", 4200)
    
    return f"""💰 *Current Fares*

• Multan: Rs. {multan:,}
• Bahawalpur: Rs. {bahawalpur:,}

To update, reply with format:
`fare multan 3500`
or
`fare bahawalpur 4200`"""


def update_fare(supabase_client, admin_phone: str, destination: str, amount: int) -> str:
    """Update fare for a destination"""
    setting = get_setting(supabase_client, "fares")
    if not setting:
        return "❌ Error fetching current fares."
    
    fares = setting.get("setting_value", {})
    old_fare = fares.get(destination.lower(), 0)
    fares[destination.lower()] = amount
    
    if update_setting(supabase_client, "fares", fares, admin_phone):
        return f"""✅ *Fare Updated!*

{destination.title()}: Rs. {old_fare:,} → Rs. {amount:,}

Change logged to audit trail."""
    else:
        return "❌ Failed to update fare. Please try again."


def get_current_dates(supabase_client) -> str:
    """Get current outbound dates for editing"""
    setting = get_setting(supabase_client, "outbound_dates")
    if not setting:
        return "Error fetching dates."
    
    dates_data = setting.get("setting_value", {})
    dates = dates_data.get("dates", [])
    description = dates_data.get("description", "")
    
    return f"""📅 *Current Outbound Dates*

{description}

Dates: {', '.join(dates)}

To update, reply with format:
`dates 2026-01-03,2026-01-04`

(Comma-separated, YYYY-MM-DD format)"""


def update_outbound_dates(supabase_client, admin_phone: str, dates: List[str], description: str = "") -> str:
    """Update outbound dates"""
    setting = get_setting(supabase_client, "outbound_dates")
    if not setting:
        return "❌ Error fetching current dates."
    
    dates_data = setting.get("setting_value", {})
    dates_data["dates"] = dates
    if description:
        dates_data["description"] = description
    
    if update_setting(supabase_client, "outbound_dates", dates_data, admin_phone):
        return f"""✅ *Dates Updated!*

New dates: {', '.join(dates)}

Change logged to audit trail."""
    else:
        return "❌ Failed to update dates. Please try again."


def get_current_return(supabase_client) -> str:
    """Get current return service info"""
    setting = get_setting(supabase_client, "return_service")
    if not setting:
        return "Error fetching return service."
    
    return_data = setting.get("setting_value", {})
    date = return_data.get("date", "")
    description = return_data.get("description", "")
    
    return f"""🔄 *Current Return Service*

Date: {date}
Description: {description}

To update, reply with format:
`return 2026-01-18 Sunday 18th January 2026`"""


def update_return_service(supabase_client, admin_phone: str, date: str, description: str) -> str:
    """Update return service"""
    return_data = {
        "date": date,
        "description": description
    }
    
    if update_setting(supabase_client, "return_service", return_data, admin_phone):
        return f"""✅ *Return Service Updated!*

New date: {date}
Description: {description}

Change logged to audit trail."""
    else:
        return "❌ Failed to update. Please try again."


def get_current_luggage(supabase_client) -> str:
    """Get current luggage policy"""
    setting = get_setting(supabase_client, "luggage_policy")
    if not setting:
        return "Error fetching luggage policy."
    
    luggage = setting.get("setting_value", {})
    
    return f"""🧳 *Current Luggage Policy*

• Max bags: {luggage.get('max_bags', 2)}
• Bag size: {luggage.get('bag_size', 'medium')}
• Hand carry: {'Yes' if luggage.get('hand_carry', True) else 'No'}

Note: {luggage.get('extra_luggage_note', 'N/A')}

To update, reply with format:
`luggage bags 2`
or
`luggage note Your new policy note here`"""


def update_luggage_policy(supabase_client, admin_phone: str, key: str, value: Any) -> str:
    """Update luggage policy"""
    setting = get_setting(supabase_client, "luggage_policy")
    if not setting:
        return "❌ Error fetching current policy."
    
    luggage = setting.get("setting_value", {})
    
    if key == "bags":
        luggage["max_bags"] = int(value)
    elif key == "note":
        luggage["extra_luggage_note"] = value
    elif key == "size":
        luggage["bag_size"] = value
    
    if update_setting(supabase_client, "luggage_policy", luggage, admin_phone):
        return f"""✅ *Luggage Policy Updated!*

Change logged to audit trail."""
    else:
        return "❌ Failed to update. Please try again."


def get_current_locations(supabase_client) -> str:
    """Get current pickup/drop locations"""
    setting = get_setting(supabase_client, "pickup_locations")
    if not setting:
        return "Error fetching locations."
    
    loc_data = setting.get("setting_value", {})
    status = loc_data.get("status", "TBD")
    locations = loc_data.get("locations", [])
    note = loc_data.get("note", "")
    
    loc_list = "\n".join([f"  • {loc}" for loc in locations]) if locations else "  None set"
    
    return f"""📍 *Current Pickup/Drop Locations*

Status: {status}
Note: {note}

Locations:
{loc_list}

To update status, reply:
`location status confirmed`

To add location, reply:
`location add GIKI Main Gate`

To set note, reply:
`location note Exact timings will be shared`"""


def update_locations(supabase_client, admin_phone: str, action: str, value: str) -> str:
    """Update pickup/drop locations"""
    setting = get_setting(supabase_client, "pickup_locations")
    if not setting:
        return "❌ Error fetching current locations."
    
    loc_data = setting.get("setting_value", {})
    
    if action == "status":
        loc_data["status"] = value
    elif action == "add":
        if "locations" not in loc_data:
            loc_data["locations"] = []
        loc_data["locations"].append(value)
    elif action == "note":
        loc_data["note"] = value
    elif action == "clear":
        loc_data["locations"] = []
    
    if update_setting(supabase_client, "pickup_locations", loc_data, admin_phone):
        return f"""✅ *Locations Updated!*

Change logged to audit trail."""
    else:
        return "❌ Failed to update. Please try again."


def get_seats_overview(supabase_client) -> str:
    """Get seats availability overview for admin"""
    try:
        dates = supabase_client.table("available_dates").select("*, buses(*)").gte("date", "2024-01-01").order("date").execute()
        
        if not dates.data:
            return "💺 *Seats Overview*\n\nNo upcoming trips found."
        
        response = "💺 *Seats Overview*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        total_available = 0
        total_booked = 0
        
        for date_info in dates.data:
            bus = date_info.get("buses", {})
            route = date_info.get("route", "Unknown")
            travel_date = date_info.get("date", "")
            seats_available = date_info.get("seats_available", 0)
            total_seats = bus.get("total_seats", 0)
            booked = total_seats - seats_available
            
            total_available += seats_available
            total_booked += booked
            
            pct = (seats_available / total_seats * 100) if total_seats > 0 else 0
            
            response += f"📅 *{travel_date}* - {route}\n"
            response += f"   🚌 {bus.get('name', 'Bus')}\n"
            response += f"   ✅ Available: {seats_available}/{total_seats}\n"
            response += f"   📊 Booked: {booked} ({100-pct:.0f}%)\n\n"
        
        response += f"━━━━━━━━━━━━━━━━━━━━━\n"
        response += f"*TOTAL:* {total_booked} booked, {total_available} available"
        
        return response
    except Exception as e:
        print(f"Error getting seats: {e}")
        return "❌ Error fetching seats data."


def rebuild_knowledge_base(supabase_client, admin_phone: str) -> str:
    """Trigger KB rebuild with latest settings"""
    try:
        # Get current settings
        settings_result = supabase_client.table("business_settings").select("*").execute()
        
        if not settings_result.data:
            return "❌ No settings found to rebuild."
        
        # Update KB entries with fresh data
        fares = next((s for s in settings_result.data if s["setting_key"] == "fares"), None)
        dates = next((s for s in settings_result.data if s["setting_key"] == "outbound_dates"), None)
        
        if fares:
            fares_val = fares["setting_value"]
            multan_fare = fares_val.get("multan", 3500)
            bwp_fare = fares_val.get("bahawalpur", 4200)
            
            # Update fare-related KB entries
            supabase_client.table("knowledge_base").update({
                "answer": f"The fare to Multan is Rs. {multan_fare:,} PKR.",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("category", "fares").ilike("question", "%multan%").execute()
            
            supabase_client.table("knowledge_base").update({
                "answer": f"The fare to Bahawalpur is Rs. {bwp_fare:,} PKR.",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("category", "fares").ilike("question", "%bahawalpur%").execute()
        
        if dates:
            dates_val = dates["setting_value"]
            desc = dates_val.get("description", "")
            
            # Update date-related KB entries
            supabase_client.table("knowledge_base").update({
                "answer": f"Outbound buses run on {desc}. Return service is available on Sunday 18th January 2026.",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("category", "dates_schedule").ilike("question", "%when%").execute()
        
        # Log the action
        log_admin_action(supabase_client, admin_phone, "Rebuilt Knowledge Base", {
            "settings_updated": len(settings_result.data)
        })
        
        return """✅ *Knowledge Base Rebuilt!*

FAQ responses now use latest settings:
• Fares updated
• Dates updated
• All KB entries refreshed

Changes logged to audit trail."""
    except Exception as e:
        print(f"KB rebuild error: {e}")
        return f"❌ Error rebuilding KB: {str(e)}"


# ============================================
# ADMIN COMMAND PARSER
# ============================================

def parse_admin_command(text: str) -> tuple[str, List[str]]:
    """Parse admin command from text"""
    parts = text.strip().split(maxsplit=2)
    command = parts[0].lower() if parts else ""
    args = parts[1:] if len(parts) > 1 else []
    return command, args


async def handle_admin_command(phone: str, text: str, supabase_client) -> Optional[str]:
    """
    Handle admin commands from WhatsApp.
    Returns response text or None if not an admin command.
    """
    if not is_admin(phone):
        return None
    
    text_lower = text.lower().strip()
    
    # Check for admin panel trigger
    if text_lower in ["admin", "admin panel", "dashboard", "/admin"]:
        return get_admin_menu_text()
    
    command, args = parse_admin_command(text)
    
    # Fare commands
    if command == "fare" and len(args) >= 2:
        destination = args[0]
        try:
            amount = int(args[1])
            return update_fare(supabase_client, phone, destination, amount)
        except ValueError:
            return "❌ Invalid amount. Use: `fare multan 3500`"
    
    # Date commands
    elif command == "dates" and args:
        dates = args[0].split(",")
        return update_outbound_dates(supabase_client, phone, dates)
    
    # Return service commands
    elif command == "return" and len(args) >= 2:
        date = args[0]
        description = args[1] if len(args) > 1 else ""
        return update_return_service(supabase_client, phone, date, description)
    
    # Luggage commands
    elif command == "luggage" and len(args) >= 2:
        key = args[0]
        value = args[1]
        return update_luggage_policy(supabase_client, phone, key, value)
    
    # Location commands
    elif command == "location" and len(args) >= 2:
        action = args[0]
        value = args[1] if len(args) > 1 else ""
        return update_locations(supabase_client, phone, action, value)
    
    return None


# ============================================
# ADMIN BUTTON HANDLERS
# ============================================

def handle_admin_button(button_id: str, supabase_client, admin_phone: str) -> str:
    """Handle admin menu button clicks"""
    
    if button_id == "admin_fares":
        return get_current_fares(supabase_client)
    
    elif button_id == "admin_dates":
        return get_current_dates(supabase_client)
    
    elif button_id == "admin_return":
        return get_current_return(supabase_client)
    
    elif button_id == "admin_luggage":
        return get_current_luggage(supabase_client)
    
    elif button_id == "admin_locations":
        return get_current_locations(supabase_client)
    
    elif button_id == "admin_seats":
        return get_seats_overview(supabase_client)
    
    elif button_id == "admin_rebuild_kb":
        return rebuild_knowledge_base(supabase_client, admin_phone)
    
    elif button_id == "admin_audit_log":
        entries = get_audit_log(supabase_client)
        return format_audit_log(entries)
    
    return "Unknown admin action."


# ============================================
# FULL DATABASE MANAGEMENT
# ============================================

# ----- BUSES MANAGEMENT -----

def get_all_buses(supabase_client) -> List[Dict[str, Any]]:
    """Get all buses (including inactive)"""
    try:
        result = supabase_client.table("buses").select("*").order("created_at").execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error getting buses: {e}")
        return []


def create_bus(supabase_client, admin_phone: str, bus_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new bus"""
    try:
        result = supabase_client.table("buses").insert(bus_data).execute()
        if result.data:
            log_admin_action(supabase_client, admin_phone, "Created bus", {"bus_name": bus_data.get("name")})
            return {"success": True, "data": result.data[0]}
        return {"success": False, "error": "Insert failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_bus(supabase_client, admin_phone: str, bus_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update a bus"""
    try:
        result = supabase_client.table("buses").update(updates).eq("id", bus_id).execute()
        if result.data:
            log_admin_action(supabase_client, admin_phone, "Updated bus", {"bus_id": bus_id, "updates": updates})
            return {"success": True, "data": result.data[0]}
        return {"success": False, "error": "Update failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_bus(supabase_client, admin_phone: str, bus_id: str) -> Dict[str, Any]:
    """Delete a bus (soft delete by setting is_active=false)"""
    try:
        result = supabase_client.table("buses").update({"is_active": False}).eq("id", bus_id).execute()
        if result.data:
            log_admin_action(supabase_client, admin_phone, "Deleted bus", {"bus_id": bus_id})
            return {"success": True}
        return {"success": False, "error": "Delete failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ----- AVAILABLE DATES MANAGEMENT -----

def get_all_available_dates(supabase_client) -> List[Dict[str, Any]]:
    """Get all available dates with bus info"""
    try:
        result = supabase_client.table("available_dates").select("*, buses(*)").order("date").execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error getting dates: {e}")
        return []


def create_available_date(supabase_client, admin_phone: str, date_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new available date"""
    try:
        result = supabase_client.table("available_dates").insert(date_data).execute()
        if result.data:
            log_admin_action(supabase_client, admin_phone, "Created available date", {
                "date": date_data.get("date"),
                "route": date_data.get("route")
            })
            return {"success": True, "data": result.data[0]}
        return {"success": False, "error": "Insert failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_available_date(supabase_client, admin_phone: str, date_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update an available date"""
    try:
        result = supabase_client.table("available_dates").update(updates).eq("id", date_id).execute()
        if result.data:
            log_admin_action(supabase_client, admin_phone, "Updated available date", {"date_id": date_id, "updates": updates})
            return {"success": True, "data": result.data[0]}
        return {"success": False, "error": "Update failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_available_date(supabase_client, admin_phone: str, date_id: str) -> Dict[str, Any]:
    """Delete an available date"""
    try:
        result = supabase_client.table("available_dates").delete().eq("id", date_id).execute()
        log_admin_action(supabase_client, admin_phone, "Deleted available date", {"date_id": date_id})
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ----- BOOKINGS MANAGEMENT -----

def get_all_bookings(supabase_client, limit: int = 50, status_filter: str = None) -> List[Dict[str, Any]]:
    """Get all bookings with optional status filter"""
    try:
        query = supabase_client.table("bookings").select("*, buses(*), available_dates(*)")
        
        if status_filter:
            query = query.eq("booking_status", status_filter)
        
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error getting bookings: {e}")
        return []


def update_booking_status(supabase_client, admin_phone: str, booking_id: str, 
                          booking_status: str = None, payment_status: str = None) -> Dict[str, Any]:
    """Update booking and/or payment status"""
    try:
        updates = {}
        if booking_status:
            updates["booking_status"] = booking_status
        if payment_status:
            updates["payment_status"] = payment_status
        
        if not updates:
            return {"success": False, "error": "No updates provided"}
        
        result = supabase_client.table("bookings").update(updates).eq("booking_id", booking_id).execute()
        if result.data:
            log_admin_action(supabase_client, admin_phone, "Updated booking status", {
                "booking_id": booking_id,
                "updates": updates
            })
            return {"success": True, "data": result.data[0]}
        return {"success": False, "error": "Update failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_booking(supabase_client, admin_phone: str, booking_id: str) -> Dict[str, Any]:
    """Delete a booking (use with caution)"""
    try:
        # First get booking details to restore seats
        booking = supabase_client.table("bookings").select("*").eq("booking_id", booking_id).single().execute()
        
        if booking.data:
            date_id = booking.data.get("date_id")
            seats_count = len(booking.data.get("selected_seats", []))
            
            # Delete the booking
            supabase_client.table("bookings").delete().eq("booking_id", booking_id).execute()
            
            # Restore seats (increment)
            if date_id and seats_count > 0:
                supabase_client.rpc("decrement_seats", {"row_id": date_id, "x": -seats_count}).execute()
            
            log_admin_action(supabase_client, admin_phone, "Deleted booking", {"booking_id": booking_id})
            return {"success": True}
        
        return {"success": False, "error": "Booking not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ----- KNOWLEDGE BASE MANAGEMENT -----

def get_all_kb_entries(supabase_client) -> List[Dict[str, Any]]:
    """Get all knowledge base entries"""
    try:
        result = supabase_client.table("knowledge_base").select("*").order("category").execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error getting KB entries: {e}")
        return []


def create_kb_entry(supabase_client, admin_phone: str, entry_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new KB entry"""
    try:
        result = supabase_client.table("knowledge_base").insert(entry_data).execute()
        if result.data:
            log_admin_action(supabase_client, admin_phone, "Created KB entry", {"question": entry_data.get("question")})
            return {"success": True, "data": result.data[0]}
        return {"success": False, "error": "Insert failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_kb_entry(supabase_client, admin_phone: str, entry_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update a KB entry"""
    try:
        updates["updated_at"] = datetime.utcnow().isoformat()
        result = supabase_client.table("knowledge_base").update(updates).eq("id", entry_id).execute()
        if result.data:
            log_admin_action(supabase_client, admin_phone, "Updated KB entry", {"entry_id": entry_id})
            return {"success": True, "data": result.data[0]}
        return {"success": False, "error": "Update failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_kb_entry(supabase_client, admin_phone: str, entry_id: str) -> Dict[str, Any]:
    """Delete a KB entry"""
    try:
        result = supabase_client.table("knowledge_base").delete().eq("id", entry_id).execute()
        log_admin_action(supabase_client, admin_phone, "Deleted KB entry", {"entry_id": entry_id})
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ----- STATISTICS -----

def get_dashboard_stats(supabase_client) -> Dict[str, Any]:
    """Get dashboard statistics"""
    try:
        # Total bookings
        bookings = supabase_client.table("bookings").select("id, booking_status, payment_status, total_amount").execute()
        
        total_bookings = len(bookings.data) if bookings.data else 0
        pending_bookings = sum(1 for b in bookings.data if b.get("booking_status") == "pending") if bookings.data else 0
        confirmed_bookings = sum(1 for b in bookings.data if b.get("booking_status") == "confirmed") if bookings.data else 0
        pending_payments = sum(1 for b in bookings.data if b.get("payment_status") == "pending") if bookings.data else 0
        total_revenue = sum(b.get("total_amount", 0) for b in bookings.data if b.get("payment_status") == "confirmed") if bookings.data else 0
        
        # Active buses
        buses = supabase_client.table("buses").select("id").eq("is_active", True).execute()
        active_buses = len(buses.data) if buses.data else 0
        
        # Upcoming dates
        from datetime import date
        dates = supabase_client.table("available_dates").select("id, seats_available").gte("date", date.today().isoformat()).execute()
        upcoming_trips = len(dates.data) if dates.data else 0
        total_seats_available = sum(d.get("seats_available", 0) for d in dates.data) if dates.data else 0
        
        return {
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "confirmed_bookings": confirmed_bookings,
            "pending_payments": pending_payments,
            "total_revenue": total_revenue,
            "active_buses": active_buses,
            "upcoming_trips": upcoming_trips,
            "total_seats_available": total_seats_available
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {}