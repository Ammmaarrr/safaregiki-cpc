import re
from typing import Optional
from session_manager import (
    ConversationState, get_state, set_state, 
    update_booking_data, get_booking_data, clear_booking_data, reset_session
)
from whatsapp_client import (
    send_welcome_message, send_main_menu, send_destination_selection,
    send_status_menu, send_faq_message, send_text_message,
    send_button_message, send_list_message, send_payment_info,
    send_screenshot_upload_link, send_admin_menu, send_admin_response
)
from database import (
    get_available_dates_by_route, get_date_info, get_available_seats,
    create_booking, get_booking_by_phone, get_all_bus_status, get_bus_by_id,
    get_supabase_client
)
from admin_handler import is_admin, handle_admin_command, handle_admin_button

# Welcome image URL - Replace with your actual image URL
WELCOME_IMAGE_URL = "https://your-domain.com/welcome-image.png"


async def handle_incoming_message(phone: str, message: dict) -> None:
    """Main handler for incoming WhatsApp messages"""
    
    # Extract message content
    message_type = message.get("type")
    
    if message_type == "text":
        text = message.get("text", {}).get("body", "").strip()
        await handle_text_message(phone, text)
    
    elif message_type == "interactive":
        interactive = message.get("interactive", {})
        interactive_type = interactive.get("type")
        
        if interactive_type == "button_reply":
            button_id = interactive.get("button_reply", {}).get("id", "")
            await handle_button_reply(phone, button_id)
        
        elif interactive_type == "list_reply":
            list_id = interactive.get("list_reply", {}).get("id", "")
            await handle_list_reply(phone, list_id)
    
    elif message_type == "image":
        # Handle image upload for payment screenshot
        image = message.get("image", {})
        await handle_image_message(phone, image)


async def handle_text_message(phone: str, text: str) -> None:
    """Handle plain text messages"""
    text_lower = text.lower().strip()
    state = get_state(phone)
    
    # Check for admin commands first
    if text_lower in ["admin", "/admin", "dashboard", "admin panel"]:
        if is_admin(phone):
            await send_admin_menu(phone)
            return
        else:
            await send_text_message(phone, "❌ You are not authorized to access the admin panel.")
            await send_main_menu(phone)
            return
    
    # Check for admin text commands (like "fare multan 3500")
    if is_admin(phone) and state == ConversationState.IDLE:
        supabase = get_supabase_client()
        admin_response = await handle_admin_command(phone, text, supabase)
        if admin_response:
            await send_admin_response(phone, admin_response)
            return
    
    # Common commands that work from any state
    if text_lower in ["hi", "hello", "hey", "start", "menu", "home"]:
        reset_session(phone)
        await send_welcome_message(phone, WELCOME_IMAGE_URL)
        return
    
    # State-specific handling
    if state == ConversationState.AWAITING_NAME:
        await handle_name_input(phone, text)
    
    elif state == ConversationState.AWAITING_REG_NUMBER:
        await handle_reg_number_input(phone, text)
    
    elif state == ConversationState.AWAITING_PHONE:
        await handle_phone_input(phone, text)
    
    elif state == ConversationState.AWAITING_SEAT:
        await handle_seat_input(phone, text)
    
    elif state == ConversationState.AWAITING_BOOKING_PHONE:
        await handle_booking_phone_lookup(phone, text)
    
    else:
        # Default: show welcome/main menu
        await send_welcome_message(phone, WELCOME_IMAGE_URL)


async def handle_button_reply(phone: str, button_id: str) -> None:
    """Handle button click responses"""
    
    # Admin menu button
    if button_id == "admin_menu":
        if is_admin(phone):
            await send_admin_menu(phone)
        else:
            await send_main_menu(phone)
        return
    
    # Main menu buttons
    if button_id == "book_seat":
        set_state(phone, ConversationState.AWAITING_ROUTE)
        await send_destination_selection(phone)
    
    elif button_id == "status":
        await send_status_menu(phone)
    
    elif button_id == "faq":
        await send_faq_message(phone)
    
    elif button_id == "main_menu":
        reset_session(phone)
        await send_main_menu(phone)
    
    # Route selection
    elif button_id == "route_giki_multan":
        update_booking_data(phone, "route", "GIKI-Multan")
        update_booking_data(phone, "from_location", "GIKI")
        update_booking_data(phone, "to_location", "Multan")
        await show_available_dates(phone, "GIKI-Multan")
    
    elif button_id == "route_multan_giki":
        update_booking_data(phone, "route", "Multan-GIKI")
        update_booking_data(phone, "from_location", "Multan")
        update_booking_data(phone, "to_location", "GIKI")
        await show_available_dates(phone, "Multan-GIKI")
    
    # Status menu
    elif button_id == "bus_status":
        await show_bus_status(phone)
    
    elif button_id == "your_booking":
        set_state(phone, ConversationState.AWAITING_BOOKING_PHONE)
        await send_text_message(
            phone,
            "📱 Please enter your phone number to find your bookings:\n\n"
            "Format: 03XXXXXXXXX"
        )
    
    # Payment
    elif button_id.startswith("upload_screenshot_"):
        booking_id = button_id.replace("upload_screenshot_", "")
        await send_screenshot_upload_link(phone, booking_id)
    
    # Date selection (handled in list_reply)
    elif button_id.startswith("date_"):
        date_id = button_id.replace("date_", "")
        await handle_date_selection(phone, date_id)


async def handle_list_reply(phone: str, list_id: str) -> None:
    """Handle list selection responses"""
    
    # Admin menu selections
    if list_id.startswith("admin_"):
        if is_admin(phone):
            supabase = get_supabase_client()
            response = handle_admin_button(list_id, supabase, phone)
            await send_admin_response(phone, response)
        else:
            await send_text_message(phone, "❌ Unauthorized access.")
            await send_main_menu(phone)
        return
    
    if list_id.startswith("date_"):
        date_id = list_id.replace("date_", "")
        await handle_date_selection(phone, date_id)
    
    elif list_id.startswith("seat_"):
        seat_number = list_id.replace("seat_", "")
        await handle_seat_selection(phone, int(seat_number))


async def show_available_dates(phone: str, route: str) -> None:
    """Show available dates for a route"""
    dates = get_available_dates_by_route(route)
    
    if not dates:
        await send_text_message(
            phone,
            "😔 Sorry, no available dates found for this route.\n\n"
            "Please check back later or try a different route."
        )
        await send_main_menu(phone)
        return
    
    # Build list sections
    sections = [{
        "title": "Available Dates",
        "rows": []
    }]
    
    for date_info in dates[:10]:  # Max 10 items
        bus = date_info.get("buses", {})
        date_str = date_info["date"]
        seats = date_info["seats_available"]
        
        row = {
            "id": f"date_{date_info['id']}",
            "title": f"{date_str}",
            "description": f"🚌 {bus.get('name', 'Bus')} | 💺 {seats} seats | Rs.{bus.get('price', 0):,}"
        }
        sections[0]["rows"].append(row)
    
    set_state(phone, ConversationState.AWAITING_DATE)
    
    await send_list_message(
        phone,
        f"📅 *Available Dates for {route}*\n\nSelect a date to continue:",
        "Select Date",
        sections,
        footer="Prices may vary by bus type"
    )


async def handle_date_selection(phone: str, date_id: str) -> None:
    """Handle date selection and move to passenger info"""
    date_info = get_date_info(date_id)
    
    if not date_info:
        await send_text_message(phone, "❌ Invalid selection. Please try again.")
        await send_main_menu(phone)
        return
    
    bus = date_info.get("buses", {})
    
    update_booking_data(phone, "date_id", date_id)
    update_booking_data(phone, "travel_date", date_info["date"])
    update_booking_data(phone, "bus_id", bus["id"])
    update_booking_data(phone, "bus_name", bus["name"])
    update_booking_data(phone, "price", bus["price"])
    
    # Show selection summary and ask for name
    summary = f"""✅ *Great Choice!*

📅 *Date:* {date_info['date']}
🚌 *Bus:* {bus['name']}
⏰ *Departure:* {bus['departure_time']}
⏰ *Arrival:* {bus['arrival_time']}
💰 *Price:* Rs. {bus['price']:,} per seat

━━━━━━━━━━━━━━━━━━━━━

Now, let's get your details for the booking.

📝 *Please enter your full name:*"""
    
    set_state(phone, ConversationState.AWAITING_NAME)
    await send_text_message(phone, summary)


async def handle_name_input(phone: str, name: str) -> None:
    """Handle passenger name input"""
    if len(name) < 3:
        await send_text_message(
            phone,
            "❌ Please enter a valid name (at least 3 characters)."
        )
        return
    
    update_booking_data(phone, "passenger_name", name)
    set_state(phone, ConversationState.AWAITING_REG_NUMBER)
    
    await send_text_message(
        phone,
        f"👤 *Name:* {name}\n\n"
        "📋 *Please enter your Registration Number:*\n\n"
        "Format: 202XXXX (e.g., 2021234)"
    )


async def handle_reg_number_input(phone: str, reg_number: str) -> None:
    """Handle registration number input"""
    # Validate format: 202XXXX
    pattern = r"^202\d{4}$"
    
    if not re.match(pattern, reg_number):
        await send_text_message(
            phone,
            "❌ Invalid registration number format.\n\n"
            "Please enter in format: 202XXXX (e.g., 2021234)"
        )
        return
    
    update_booking_data(phone, "student_id", reg_number)
    set_state(phone, ConversationState.AWAITING_PHONE)
    
    await send_text_message(
        phone,
        f"🎓 *Reg Number:* {reg_number}\n\n"
        "📱 *Please enter your phone number:*\n\n"
        "Format: 03XXXXXXXXX (e.g., 03001234567)"
    )


async def handle_phone_input(phone: str, phone_number: str) -> None:
    """Handle phone number input"""
    # Validate format: 03XXXXXXXXX
    pattern = r"^03\d{9}$"
    
    # Clean the input
    clean_phone = phone_number.replace("-", "").replace(" ", "")
    
    if not re.match(pattern, clean_phone):
        await send_text_message(
            phone,
            "❌ Invalid phone number format.\n\n"
            "Please enter in format: 03XXXXXXXXX (e.g., 03001234567)"
        )
        return
    
    update_booking_data(phone, "passenger_phone", clean_phone)
    
    # Show available seats
    await show_available_seats(phone)


async def show_available_seats(phone: str) -> None:
    """Show available seats for selection"""
    booking_data = get_booking_data(phone)
    date_id = booking_data.get("date_id")
    
    available_seats = get_available_seats(date_id)
    
    if not available_seats:
        await send_text_message(
            phone,
            "😔 Sorry, all seats are booked for this date.\n\n"
            "Please select a different date."
        )
        clear_booking_data(phone)
        await send_main_menu(phone)
        return
    
    # Format seats display
    seats_display = ", ".join([str(s) for s in available_seats[:20]])  # Show first 20
    
    set_state(phone, ConversationState.AWAITING_SEAT)
    
    await send_text_message(
        phone,
        f"📱 *Phone:* {booking_data.get('passenger_phone')}\n\n"
        f"💺 *Available Seats:*\n{seats_display}\n\n"
        "Please type the seat number you want to book:"
    )


async def handle_seat_input(phone: str, seat_text: str) -> None:
    """Handle seat selection input"""
    try:
        seat_number = int(seat_text.strip())
    except ValueError:
        await send_text_message(phone, "❌ Please enter a valid seat number.")
        return
    
    booking_data = get_booking_data(phone)
    date_id = booking_data.get("date_id")
    available_seats = get_available_seats(date_id)
    
    if seat_number not in available_seats:
        await send_text_message(
            phone,
            f"❌ Seat {seat_number} is not available.\n\n"
            "Please select from the available seats."
        )
        return
    
    update_booking_data(phone, "selected_seats", [seat_number])
    
    # Show booking summary and confirm
    await show_booking_confirmation(phone)


async def handle_seat_selection(phone: str, seat_number: int) -> None:
    """Handle seat selection from list"""
    booking_data = get_booking_data(phone)
    date_id = booking_data.get("date_id")
    available_seats = get_available_seats(date_id)
    
    if seat_number not in available_seats:
        await send_text_message(
            phone,
            f"❌ Seat {seat_number} is no longer available.\n\n"
            "Please select another seat."
        )
        return
    
    update_booking_data(phone, "selected_seats", [seat_number])
    await show_booking_confirmation(phone)


async def show_booking_confirmation(phone: str) -> None:
    """Show booking summary and payment button"""
    booking_data = get_booking_data(phone)
    
    price = booking_data.get("price", 0)
    seats = booking_data.get("selected_seats", [])
    total_amount = price * len(seats)
    
    summary = f"""📋 *Booking Summary*

━━━━━━━━━━━━━━━━━━━━━

🚌 *Route:* {booking_data.get('from_location')} → {booking_data.get('to_location')}
📅 *Date:* {booking_data.get('travel_date')}
🚍 *Bus:* {booking_data.get('bus_name')}

━━━━━━━━━━━━━━━━━━━━━

👤 *Passenger Details:*
• Name: {booking_data.get('passenger_name')}
• Reg No: {booking_data.get('student_id')}
• Phone: {booking_data.get('passenger_phone')}

━━━━━━━━━━━━━━━━━━━━━

💺 *Seat(s):* {', '.join(map(str, seats))}
💰 *Total Amount:* Rs. {total_amount:,}

━━━━━━━━━━━━━━━━━━━━━"""
    
    await send_text_message(phone, summary)
    
    buttons = [
        {"id": "confirm_booking", "title": "✅ Confirm & Pay"},
        {"id": "main_menu", "title": "❌ Cancel"}
    ]
    
    set_state(phone, ConversationState.AWAITING_PAYMENT_CONFIRMATION)
    update_booking_data(phone, "total_amount", total_amount)
    
    await send_button_message(
        phone,
        "Please confirm your booking to proceed to payment.",
        buttons
    )


async def process_booking_confirmation(phone: str) -> None:
    """Create the booking and show payment info"""
    booking_data = get_booking_data(phone)
    
    # Create booking in database
    booking = create_booking(
        bus_id=booking_data.get("bus_id"),
        date_id=booking_data.get("date_id"),
        from_location=booking_data.get("from_location"),
        to_location=booking_data.get("to_location"),
        travel_date=booking_data.get("travel_date"),
        passenger_name=booking_data.get("passenger_name"),
        passenger_phone=booking_data.get("passenger_phone"),
        passenger_cnic=booking_data.get("student_id"),  # Using student ID as CNIC
        student_id=booking_data.get("student_id"),
        selected_seats=booking_data.get("selected_seats"),
        total_amount=booking_data.get("total_amount"),
        payment_method="bank_transfer"
    )
    
    if booking:
        booking_id = booking["booking_id"]
        total_amount = booking_data.get("total_amount")
        
        success_msg = f"""🎉 *Booking Created Successfully!*

Your booking ID: *{booking_id}*

Please save this ID for your records."""
        
        await send_text_message(phone, success_msg)
        await send_payment_info(phone, booking_id, total_amount)
        
        clear_booking_data(phone)
    else:
        await send_text_message(
            phone,
            "❌ Sorry, there was an error creating your booking.\n\n"
            "Please try again or contact support."
        )
        await send_main_menu(phone)


async def show_bus_status(phone: str) -> None:
    """Show all bus status information"""
    bus_status = get_all_bus_status()
    
    if not bus_status:
        await send_text_message(phone, "No buses available at the moment.")
        await send_main_menu(phone)
        return
    
    status_text = "🚌 *Bus Status*\n\n"
    
    for item in bus_status:
        bus = item["bus"]
        dates = item["available_dates"]
        
        status_text += f"━━━━━━━━━━━━━━━━━━━━━\n"
        status_text += f"*{bus['name']}*\n"
        status_text += f"Type: {bus['bus_type'].title()}\n"
        status_text += f"Departure: {bus['departure_time']} | Arrival: {bus['arrival_time']}\n"
        status_text += f"Duration: {bus['duration']}\n"
        status_text += f"Price: Rs. {bus['price']:,}\n"
        status_text += f"Amenities: {', '.join(bus.get('amenities', []))}\n\n"
        
        if dates:
            status_text += "*Available Dates:*\n"
            for date_info in dates[:5]:  # Show first 5 dates
                status_text += f"• {date_info['date']} ({date_info['route']}): {date_info['seats_available']} seats\n"
        else:
            status_text += "*No upcoming dates available*\n"
        
        status_text += "\n"
    
    await send_text_message(phone, status_text)
    
    buttons = [{"id": "main_menu", "title": "🔙 Main Menu"}]
    await send_button_message(phone, "Need anything else?", buttons)


async def handle_booking_phone_lookup(phone: str, input_phone: str) -> None:
    """Look up bookings by phone number"""
    # Validate format: 03XXXXXXXXX
    pattern = r"^03\d{9}$"
    clean_phone = input_phone.replace("-", "").replace(" ", "")
    
    if not re.match(pattern, clean_phone):
        await send_text_message(
            phone,
            "❌ Invalid phone number format.\n\n"
            "Please enter in format: 03XXXXXXXXX"
        )
        return
    
    bookings = get_booking_by_phone(clean_phone)
    
    if not bookings:
        await send_text_message(
            phone,
            f"📭 No bookings found for {clean_phone}.\n\n"
            "Make sure you entered the correct phone number."
        )
        set_state(phone, ConversationState.IDLE)
        await send_main_menu(phone)
        return
    
    response = f"🎫 *Your Bookings ({clean_phone})*\n\n"
    
    for booking in bookings[:5]:  # Show last 5 bookings
        bus = booking.get("buses", {})
        
        # Payment status emoji
        payment_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "rejected": "❌"
        }.get(booking["payment_status"], "❓")
        
        # Booking status emoji
        booking_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "cancelled": "❌"
        }.get(booking["booking_status"], "❓")
        
        response += f"━━━━━━━━━━━━━━━━━━━━━\n"
        response += f"*Booking ID:* {booking['booking_id']}\n"
        response += f"*Route:* {booking['from_location']} → {booking['to_location']}\n"
        response += f"*Date:* {booking['travel_date']}\n"
        response += f"*Bus:* {bus.get('name', 'N/A')}\n"
        response += f"*Seat(s):* {', '.join(map(str, booking.get('selected_seats', [])))}\n"
        response += f"*Amount:* Rs. {booking['total_amount']:,}\n"
        response += f"*Payment Status:* {payment_emoji} {booking['payment_status'].title()}\n"
        response += f"*Booking Status:* {booking_emoji} {booking['booking_status'].title()}\n\n"
    
    await send_text_message(phone, response)
    set_state(phone, ConversationState.IDLE)
    
    buttons = [{"id": "main_menu", "title": "🔙 Main Menu"}]
    await send_button_message(phone, "Need anything else?", buttons)


async def handle_image_message(phone: str, image: dict) -> None:
    """Handle image uploads (payment screenshots)"""
    await send_text_message(
        phone,
        "📸 *Image Received*\n\n"
        "Thank you for uploading your payment screenshot.\n\n"
        "To link it to your booking, please use the upload link "
        "provided after your booking was created.\n\n"
        "Our team will verify your payment within 24 hours."
    )
    
    buttons = [{"id": "main_menu", "title": "🔙 Main Menu"}]
    await send_button_message(phone, "Need anything else?", buttons)


async def handle_confirm_booking_button(phone: str) -> None:
    """Handle the confirm booking button"""
    await process_booking_confirmation(phone)