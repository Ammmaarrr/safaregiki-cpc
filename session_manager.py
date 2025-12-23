from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

# In-memory session storage (consider Redis for production)
user_sessions: Dict[str, Dict[str, Any]] = {}

# Session expiry time (30 minutes)
SESSION_EXPIRY_MINUTES = 30


class ConversationState:
    """Conversation states for the booking flow"""
    IDLE = "idle"
    
    # Booking flow states
    AWAITING_ROUTE = "awaiting_route"
    AWAITING_DATE = "awaiting_date"
    AWAITING_NAME = "awaiting_name"
    AWAITING_REG_NUMBER = "awaiting_reg_number"
    AWAITING_PHONE = "awaiting_phone"
    AWAITING_SEAT = "awaiting_seat"
    AWAITING_PAYMENT_CONFIRMATION = "awaiting_payment_confirmation"
    
    # Status flow states
    AWAITING_BOOKING_PHONE = "awaiting_booking_phone"
    
    # FAQ states
    FAQ_QUESTION = "faq_question"
    
    # Admin states
    ADMIN_EDITING = "admin_editing"


def get_session(phone: str) -> Dict[str, Any]:
    """Get or create a user session"""
    now = datetime.now()
    
    if phone in user_sessions:
        session = user_sessions[phone]
        # Check if session has expired
        if session.get("last_activity"):
            last_activity = datetime.fromisoformat(session["last_activity"])
            if now - last_activity > timedelta(minutes=SESSION_EXPIRY_MINUTES):
                # Session expired, create new one
                user_sessions[phone] = create_new_session()
    else:
        user_sessions[phone] = create_new_session()
    
    # Update last activity
    user_sessions[phone]["last_activity"] = now.isoformat()
    return user_sessions[phone]


def create_new_session() -> Dict[str, Any]:
    """Create a new session with default values"""
    return {
        "state": ConversationState.IDLE,
        "booking_data": {},
        "last_activity": datetime.now().isoformat()
    }


def update_session(phone: str, updates: Dict[str, Any]) -> None:
    """Update session data"""
    session = get_session(phone)
    session.update(updates)
    session["last_activity"] = datetime.now().isoformat()
    user_sessions[phone] = session


def set_state(phone: str, state: str) -> None:
    """Set the conversation state"""
    session = get_session(phone)
    session["state"] = state
    session["last_activity"] = datetime.now().isoformat()
    user_sessions[phone] = session


def get_state(phone: str) -> str:
    """Get the current conversation state"""
    session = get_session(phone)
    return session.get("state", ConversationState.IDLE)


def update_booking_data(phone: str, key: str, value: Any) -> None:
    """Update booking data in session"""
    session = get_session(phone)
    if "booking_data" not in session:
        session["booking_data"] = {}
    session["booking_data"][key] = value
    session["last_activity"] = datetime.now().isoformat()
    user_sessions[phone] = session


def get_booking_data(phone: str) -> Dict[str, Any]:
    """Get all booking data from session"""
    session = get_session(phone)
    return session.get("booking_data", {})


def clear_booking_data(phone: str) -> None:
    """Clear booking data and reset to idle"""
    session = get_session(phone)
    session["booking_data"] = {}
    session["state"] = ConversationState.IDLE
    user_sessions[phone] = session


def reset_session(phone: str) -> None:
    """Completely reset a user's session"""
    user_sessions[phone] = create_new_session()