from supabase import create_client, Client
from config import get_settings
from typing import Optional, List, Dict, Any
from datetime import date
import uuid

settings = get_settings()
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)


def get_supabase_client() -> Client:
    """Get the Supabase client instance"""
    return supabase


# ============== BUS OPERATIONS ==============

def get_active_buses() -> List[Dict[str, Any]]:
    """Get all active buses"""
    response = supabase.table("buses").select("*").eq("is_active", True).execute()
    return response.data


def get_bus_by_id(bus_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific bus by ID"""
    response = supabase.table("buses").select("*").eq("id", bus_id).single().execute()
    return response.data if response.data else None


# ============== AVAILABLE DATES OPERATIONS ==============

def get_available_dates_by_route(route: str) -> List[Dict[str, Any]]:
    """Get available dates for a specific route"""
    response = (
        supabase.table("available_dates")
        .select("*, buses(*)")
        .eq("route", route)
        .gte("date", date.today().isoformat())
        .gt("seats_available", 0)
        .order("date")
        .execute()
    )
    return response.data


def get_date_info(date_id: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific date"""
    response = (
        supabase.table("available_dates")
        .select("*, buses(*)")
        .eq("id", date_id)
        .single()
        .execute()
    )
    return response.data if response.data else None


def get_available_seats(date_id: str) -> List[int]:
    """Get list of available seat numbers for a date"""
    date_info = get_date_info(date_id)
    if not date_info:
        return []
    
    total_seats = date_info["buses"]["total_seats"]
    
    # Get booked seats for this date
    bookings = (
        supabase.table("bookings")
        .select("selected_seats")
        .eq("date_id", date_id)
        .neq("booking_status", "cancelled")
        .execute()
    )
    
    booked_seats = set()
    for booking in bookings.data:
        if booking.get("selected_seats"):
            booked_seats.update(booking["selected_seats"])
    
    # Return available seats
    all_seats = set(range(1, total_seats + 1))
    return sorted(list(all_seats - booked_seats))


# ============== BOOKING OPERATIONS ==============

def generate_booking_id() -> str:
    """Generate a unique booking ID"""
    return f"SFG-{uuid.uuid4().hex[:8].upper()}"


def create_booking(
    bus_id: str,
    date_id: str,
    from_location: str,
    to_location: str,
    travel_date: str,
    passenger_name: str,
    passenger_phone: str,
    passenger_cnic: str,
    student_id: str,
    selected_seats: List[int],
    total_amount: int,
    payment_method: str = "bank_transfer"
) -> Optional[Dict[str, Any]]:
    """Create a new booking"""
    booking_id = generate_booking_id()
    
    booking_data = {
        "booking_id": booking_id,
        "bus_id": bus_id,
        "date_id": date_id,
        "from_location": from_location,
        "to_location": to_location,
        "travel_date": travel_date,
        "passenger_name": passenger_name,
        "passenger_phone": passenger_phone,
        "passenger_cnic": passenger_cnic,
        "emergency_contact": passenger_phone,  # Using same phone as emergency
        "student_id": student_id,
        "selected_seats": selected_seats,
        "total_amount": total_amount,
        "payment_method": payment_method,
        "payment_status": "pending",
        "booking_status": "pending"
    }
    
    response = supabase.table("bookings").insert(booking_data).execute()
    
    if response.data:
        # Decrement available seats
        supabase.rpc("decrement_seats", {"row_id": date_id, "x": len(selected_seats)}).execute()
        return response.data[0]
    return None


def get_booking_by_phone(phone: str) -> List[Dict[str, Any]]:
    """Get all bookings for a phone number"""
    response = (
        supabase.table("bookings")
        .select("*, buses(*), available_dates(*)")
        .eq("passenger_phone", phone)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def get_booking_by_id(booking_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific booking by ID"""
    response = (
        supabase.table("bookings")
        .select("*, buses(*), available_dates(*)")
        .eq("booking_id", booking_id)
        .single()
        .execute()
    )
    return response.data if response.data else None


def update_payment_screenshot(booking_id: str, screenshot_url: str) -> bool:
    """Update booking with payment screenshot URL"""
    response = (
        supabase.table("bookings")
        .update({"payment_screenshot_url": screenshot_url})
        .eq("booking_id", booking_id)
        .execute()
    )
    return len(response.data) > 0


# ============== BUS STATUS OPERATIONS ==============

def get_all_bus_status() -> List[Dict[str, Any]]:
    """Get status of all buses with available dates"""
    buses = get_active_buses()
    result = []
    
    for bus in buses:
        dates = (
            supabase.table("available_dates")
            .select("*")
            .eq("bus_id", bus["id"])
            .gte("date", date.today().isoformat())
            .order("date")
            .execute()
        )
        
        bus_info = {
            "bus": bus,
            "available_dates": dates.data
        }
        result.append(bus_info)
    
    return result