from fastapi import FastAPI, Request, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import PlainTextResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from message_handler import (
    handle_incoming_message, handle_button_reply, 
    process_booking_confirmation
)
from session_manager import get_state, ConversationState
from database import update_payment_screenshot, get_booking_by_id
import json

app = FastAPI(
    title="Safar-e-GIKI WhatsApp Bot",
    description="WhatsApp Bot Backend for Bus Booking System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Safar-e-GIKI WhatsApp Bot",
        "version": "1.0.0"
    }


@app.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    """
    Webhook verification endpoint for Meta WhatsApp API.
    Meta sends a GET request to verify the webhook URL.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.verify_token:
        print(f"Webhook verified successfully!")
        return PlainTextResponse(content=hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook/whatsapp")
async def webhook_handler(request: Request):
    """
    Main webhook endpoint that receives WhatsApp messages.
    """
    try:
        body = await request.json()
        print(f"Received webhook: {json.dumps(body, indent=2)}")
        
        # Extract message data
        entry = body.get("entry", [])
        
        for e in entry:
            changes = e.get("changes", [])
            
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                for message in messages:
                    # Get sender's phone number
                    sender = message.get("from", "")
                    
                    # Handle button confirmation separately
                    if message.get("type") == "interactive":
                        interactive = message.get("interactive", {})
                        if interactive.get("type") == "button_reply":
                            button_id = interactive.get("button_reply", {}).get("id", "")
                            
                            # Special handling for confirm_booking
                            if button_id == "confirm_booking":
                                state = get_state(sender)
                                if state == ConversationState.AWAITING_PAYMENT_CONFIRMATION:
                                    await process_booking_confirmation(sender)
                                    return JSONResponse(content={"status": "ok"})
                    
                    # Process the message
                    await handle_incoming_message(sender, message)
        
        return JSONResponse(content={"status": "ok"})
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        # Return 200 to prevent Meta from retrying
        return JSONResponse(content={"status": "error", "message": str(e)})


@app.get("/upload/{booking_id}", response_class=HTMLResponse)
async def upload_page(booking_id: str):
    """
    Render a simple HTML page for uploading payment screenshots.
    """
    booking = get_booking_by_id(booking_id)
    
    if not booking:
        return HTMLResponse(
            content="<h1>Booking not found</h1><p>Please check your booking ID.</p>",
            status_code=404
        )
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload Payment Screenshot - Safar-e-GIKI</title>
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 16px;
                padding: 32px;
                max-width: 420px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .logo {{
                text-align: center;
                margin-bottom: 24px;
            }}
            .logo h1 {{
                color: #667eea;
                font-size: 24px;
            }}
            .booking-info {{
                background: #f7f7f7;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 24px;
            }}
            .booking-info p {{
                margin: 8px 0;
                color: #333;
            }}
            .booking-info strong {{
                color: #667eea;
            }}
            .upload-area {{
                border: 2px dashed #667eea;
                border-radius: 8px;
                padding: 32px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
                margin-bottom: 16px;
            }}
            .upload-area:hover {{
                background: #f0f0ff;
            }}
            .upload-area.dragover {{
                background: #e0e0ff;
                border-color: #764ba2;
            }}
            input[type="file"] {{
                display: none;
            }}
            .btn {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                width: 100%;
                transition: transform 0.2s;
            }}
            .btn:hover {{
                transform: translateY(-2px);
            }}
            .btn:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
            }}
            .preview {{
                max-width: 100%;
                border-radius: 8px;
                margin: 16px 0;
                display: none;
            }}
            .success {{
                background: #d4edda;
                color: #155724;
                padding: 16px;
                border-radius: 8px;
                margin-top: 16px;
                display: none;
            }}
            .error {{
                background: #f8d7da;
                color: #721c24;
                padding: 16px;
                border-radius: 8px;
                margin-top: 16px;
                display: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <h1>🚌 Safar-e-GIKI</h1>
                <p>Upload Payment Screenshot</p>
            </div>
            
            <div class="booking-info">
                <p><strong>Booking ID:</strong> {booking['booking_id']}</p>
                <p><strong>Passenger:</strong> {booking['passenger_name']}</p>
                <p><strong>Route:</strong> {booking['from_location']} → {booking['to_location']}</p>
                <p><strong>Amount:</strong> Rs. {booking['total_amount']:,}</p>
            </div>
            
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="upload-area" id="dropZone">
                    <p>📷 Click or drag to upload screenshot</p>
                    <input type="file" id="fileInput" name="file" accept="image/*" required>
                </div>
                
                <img id="preview" class="preview" alt="Preview">
                
                <button type="submit" class="btn" id="submitBtn" disabled>
                    Upload Screenshot
                </button>
            </form>
            
            <div class="success" id="successMsg">
                ✅ Screenshot uploaded successfully! Your payment will be verified within 24 hours.
            </div>
            
            <div class="error" id="errorMsg">
                ❌ Upload failed. Please try again.
            </div>
        </div>
        
        <script>
            const dropZone = document.getElementById('dropZone');
            const fileInput = document.getElementById('fileInput');
            const preview = document.getElementById('preview');
            const submitBtn = document.getElementById('submitBtn');
            const form = document.getElementById('uploadForm');
            const successMsg = document.getElementById('successMsg');
            const errorMsg = document.getElementById('errorMsg');
            
            dropZone.addEventListener('click', () => fileInput.click());
            
            dropZone.addEventListener('dragover', (e) => {{
                e.preventDefault();
                dropZone.classList.add('dragover');
            }});
            
            dropZone.addEventListener('dragleave', () => {{
                dropZone.classList.remove('dragover');
            }});
            
            dropZone.addEventListener('drop', (e) => {{
                e.preventDefault();
                dropZone.classList.remove('dragover');
                fileInput.files = e.dataTransfer.files;
                handleFile(e.dataTransfer.files[0]);
            }});
            
            fileInput.addEventListener('change', (e) => {{
                handleFile(e.target.files[0]);
            }});
            
            function handleFile(file) {{
                if (file && file.type.startsWith('image/')) {{
                    const reader = new FileReader();
                    reader.onload = (e) => {{
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                        submitBtn.disabled = false;
                    }};
                    reader.readAsDataURL(file);
                }}
            }}
            
            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                submitBtn.disabled = true;
                submitBtn.textContent = 'Uploading...';
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                try {{
                    const response = await fetch('/upload/{booking_id}/submit', {{
                        method: 'POST',
                        body: formData
                    }});
                    
                    if (response.ok) {{
                        successMsg.style.display = 'block';
                        errorMsg.style.display = 'none';
                        form.style.display = 'none';
                    }} else {{
                        throw new Error('Upload failed');
                    }}
                }} catch (error) {{
                    errorMsg.style.display = 'block';
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Upload Screenshot';
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@app.post("/upload/{booking_id}/submit")
async def submit_upload(booking_id: str, file: UploadFile = File(...)):
    """
    Handle the actual file upload.
    In production, you would upload to Supabase storage or S3.
    """
    booking = get_booking_by_id(booking_id)
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # In production, upload to Supabase storage:
    # 1. Read file content
    # 2. Upload to supabase.storage.from_('booking-attachments').upload(...)
    # 3. Get public URL
    # 4. Update booking with screenshot URL
    
    # For now, we'll create a placeholder URL
    # Replace this with actual Supabase storage upload
    screenshot_url = f"{settings.app_url}/screenshots/{booking_id}/{file.filename}"
    
    # Update booking with screenshot URL
    success = update_payment_screenshot(booking_id, screenshot_url)
    
    if success:
        return JSONResponse(content={
            "status": "success",
            "message": "Screenshot uploaded successfully",
            "url": screenshot_url
        })
    else:
        raise HTTPException(status_code=500, detail="Failed to update booking")


@app.get("/api/bookings/{phone}")
async def get_user_bookings(phone: str):
    """API endpoint to get bookings by phone number"""
    from database import get_booking_by_phone
    
    bookings = get_booking_by_phone(phone)
    return JSONResponse(content={"bookings": bookings})


@app.get("/api/buses")
async def get_buses():
    """API endpoint to get all active buses"""
    from database import get_active_buses
    
    buses = get_active_buses()
    return JSONResponse(content={"buses": buses})


@app.get("/api/dates/{route}")
async def get_available_dates(route: str):
    """API endpoint to get available dates for a route"""
    from database import get_available_dates_by_route
    
    dates = get_available_dates_by_route(route)
    return JSONResponse(content={"dates": dates})


# ============================================
# ADMIN DASHBOARD ENDPOINTS
# ============================================

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve the admin dashboard HTML"""
    try:
        with open("templates/admin_dashboard.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin dashboard not found</h1>", status_code=404)


@app.post("/admin/login")
async def admin_login(request: Request):
    """Admin login endpoint"""
    from admin_handler import is_admin
    
    data = await request.json()
    phone = data.get("phone", "")
    pin = data.get("pin", "")
    
    # Check if phone is in admin list
    if is_admin(phone):
        # In production, verify PIN against stored hash
        return JSONResponse(content={"status": "success", "token": "admin_authenticated"})
    
    raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/admin/settings/{key}")
async def get_admin_setting(key: str):
    """Get a specific business setting"""
    from admin_handler import get_setting
    from database import get_supabase_client
    
    supabase = get_supabase_client()
    setting = get_setting(supabase, key)
    
    if setting:
        return JSONResponse(content=setting)
    raise HTTPException(status_code=404, detail="Setting not found")


@app.post("/admin/settings/fares")
async def update_fares(request: Request):
    """Update fare settings"""
    from admin_handler import update_fare, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    destination = data.get("destination")
    amount = data.get("amount")
    
    result = update_fare(supabase, admin_phone, destination, amount)
    return JSONResponse(content={"status": "success", "message": result})


@app.post("/admin/settings/dates")
async def update_dates(request: Request):
    """Update outbound dates"""
    from admin_handler import update_outbound_dates, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    dates = data.get("dates", [])
    description = data.get("description", "")
    
    result = update_outbound_dates(supabase, admin_phone, dates, description)
    return JSONResponse(content={"status": "success", "message": result})


@app.post("/admin/settings/return")
async def update_return(request: Request):
    """Update return service"""
    from admin_handler import update_return_service, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    date = data.get("date", "")
    description = data.get("description", "")
    
    result = update_return_service(supabase, admin_phone, date, description)
    return JSONResponse(content={"status": "success", "message": result})


@app.post("/admin/settings/luggage")
async def update_luggage(request: Request):
    """Update luggage policy"""
    from admin_handler import update_luggage_policy, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    key = data.get("key")
    value = data.get("value")
    
    result = update_luggage_policy(supabase, admin_phone, key, value)
    return JSONResponse(content={"status": "success", "message": result})


@app.post("/admin/settings/locations")
async def update_locations(request: Request):
    """Update pickup/drop locations"""
    from admin_handler import update_locations as admin_update_locations, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    action = data.get("action")
    value = data.get("value")
    
    result = admin_update_locations(supabase, admin_phone, action, value)
    return JSONResponse(content={"status": "success", "message": result})


@app.get("/admin/seats")
async def get_seats_overview():
    """Get seats availability overview"""
    from admin_handler import get_seats_overview
    from database import get_supabase_client
    
    supabase = get_supabase_client()
    overview = get_seats_overview(supabase)
    return JSONResponse(content={"overview": overview})


@app.post("/admin/rebuild-kb")
async def rebuild_kb(request: Request):
    """Rebuild knowledge base"""
    from admin_handler import rebuild_knowledge_base, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    result = rebuild_knowledge_base(supabase, admin_phone)
    return JSONResponse(content={"status": "success", "message": result})


@app.get("/admin/audit-log")
async def get_audit_log():
    """Get audit log entries"""
    from admin_handler import get_audit_log
    from database import get_supabase_client
    
    supabase = get_supabase_client()
    entries = get_audit_log(supabase, limit=20)
    return JSONResponse(content={"entries": entries})


# ============================================
# FULL DATABASE MANAGEMENT ENDPOINTS
# ============================================

# ----- DASHBOARD STATS -----

@app.get("/admin/stats")
async def get_stats():
    """Get dashboard statistics"""
    from admin_handler import get_dashboard_stats
    from database import get_supabase_client
    
    supabase = get_supabase_client()
    stats = get_dashboard_stats(supabase)
    return JSONResponse(content=stats)


# ----- BUSES CRUD -----

@app.get("/admin/buses")
async def admin_get_buses():
    """Get all buses (including inactive)"""
    from admin_handler import get_all_buses
    from database import get_supabase_client
    
    supabase = get_supabase_client()
    buses = get_all_buses(supabase)
    return JSONResponse(content={"buses": buses})


@app.post("/admin/buses")
async def admin_create_bus(request: Request):
    """Create a new bus"""
    from admin_handler import create_bus, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    bus_data = {
        "name": data.get("name"),
        "bus_type": data.get("bus_type", "business"),
        "total_seats": data.get("total_seats", 27),
        "price": data.get("price", 3500),
        "departure_time": data.get("departure_time", "08:00"),
        "arrival_time": data.get("arrival_time", "14:00"),
        "duration": data.get("duration", "6 hrs"),
        "amenities": data.get("amenities", []),
        "is_active": data.get("is_active", True)
    }
    
    result = create_bus(supabase, admin_phone, bus_data)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


@app.put("/admin/buses/{bus_id}")
async def admin_update_bus(bus_id: str, request: Request):
    """Update a bus"""
    from admin_handler import update_bus, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    
    # Remove admin_phone from updates
    updates = {k: v for k, v in data.items() if k != "admin_phone"}
    
    result = update_bus(supabase, admin_phone, bus_id, updates)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


@app.delete("/admin/buses/{bus_id}")
async def admin_delete_bus(bus_id: str, request: Request):
    """Delete a bus (soft delete)"""
    from admin_handler import delete_bus, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    result = delete_bus(supabase, admin_phone, bus_id)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


# ----- AVAILABLE DATES CRUD -----

@app.get("/admin/available-dates")
async def admin_get_available_dates():
    """Get all available dates"""
    from admin_handler import get_all_available_dates
    from database import get_supabase_client
    
    supabase = get_supabase_client()
    dates = get_all_available_dates(supabase)
    return JSONResponse(content={"dates": dates})


@app.post("/admin/available-dates")
async def admin_create_available_date(request: Request):
    """Create a new available date"""
    from admin_handler import create_available_date, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    date_data = {
        "date": data.get("date"),
        "route": data.get("route"),
        "bus_id": data.get("bus_id"),
        "seats_available": data.get("seats_available")
    }
    
    result = create_available_date(supabase, admin_phone, date_data)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


@app.put("/admin/available-dates/{date_id}")
async def admin_update_available_date(date_id: str, request: Request):
    """Update an available date"""
    from admin_handler import update_available_date, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    updates = {k: v for k, v in data.items() if k != "admin_phone"}
    
    result = update_available_date(supabase, admin_phone, date_id, updates)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


@app.delete("/admin/available-dates/{date_id}")
async def admin_delete_available_date(date_id: str, request: Request):
    """Delete an available date"""
    from admin_handler import delete_available_date, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    result = delete_available_date(supabase, admin_phone, date_id)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


# ----- BOOKINGS MANAGEMENT -----

@app.get("/admin/bookings")
async def admin_get_bookings(status: str = None, limit: int = 50):
    """Get all bookings with optional status filter"""
    from admin_handler import get_all_bookings
    from database import get_supabase_client
    
    supabase = get_supabase_client()
    bookings = get_all_bookings(supabase, limit=limit, status_filter=status)
    return JSONResponse(content={"bookings": bookings})


@app.put("/admin/bookings/{booking_id}")
async def admin_update_booking(booking_id: str, request: Request):
    """Update booking status"""
    from admin_handler import update_booking_status, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    result = update_booking_status(
        supabase, 
        admin_phone, 
        booking_id,
        booking_status=data.get("booking_status"),
        payment_status=data.get("payment_status")
    )
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


@app.delete("/admin/bookings/{booking_id}")
async def admin_delete_booking(booking_id: str, request: Request):
    """Delete a booking"""
    from admin_handler import delete_booking, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    result = delete_booking(supabase, admin_phone, booking_id)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


# ----- KNOWLEDGE BASE CRUD -----

@app.get("/admin/knowledge-base")
async def admin_get_kb():
    """Get all knowledge base entries"""
    from admin_handler import get_all_kb_entries
    from database import get_supabase_client
    
    supabase = get_supabase_client()
    entries = get_all_kb_entries(supabase)
    return JSONResponse(content={"entries": entries})


@app.post("/admin/knowledge-base")
async def admin_create_kb_entry(request: Request):
    """Create a new KB entry"""
    from admin_handler import create_kb_entry, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    entry_data = {
        "category": data.get("category"),
        "question": data.get("question"),
        "answer": data.get("answer"),
        "keywords": data.get("keywords", []),
        "is_active": data.get("is_active", True)
    }
    
    result = create_kb_entry(supabase, admin_phone, entry_data)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


@app.put("/admin/knowledge-base/{entry_id}")
async def admin_update_kb_entry(entry_id: str, request: Request):
    """Update a KB entry"""
    from admin_handler import update_kb_entry, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    updates = {k: v for k, v in data.items() if k != "admin_phone"}
    
    result = update_kb_entry(supabase, admin_phone, entry_id, updates)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


@app.delete("/admin/knowledge-base/{entry_id}")
async def admin_delete_kb_entry(entry_id: str, request: Request):
    """Delete a KB entry"""
    from admin_handler import delete_kb_entry, is_admin
    from database import get_supabase_client
    
    data = await request.json()
    admin_phone = data.get("admin_phone", "")
    
    if not is_admin(admin_phone):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    supabase = get_supabase_client()
    result = delete_kb_entry(supabase, admin_phone, entry_id)
    if result.get("success"):
        return JSONResponse(content=result)
    raise HTTPException(status_code=400, detail=result.get("error"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)