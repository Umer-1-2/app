from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import asyncio
import resend
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# Resend Email
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str  # 'employee' or 'employer'

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    role: str
    created_at: str

class AttendancePunchIn(BaseModel):
    pass

class AttendanceAction(BaseModel):
    pass

class AttendanceRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    attendance_id: str
    user_id: str
    user_name: str
    user_email: str
    date: str
    punch_in: Optional[str] = None
    punch_out: Optional[str] = None
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    total_hours: Optional[float] = None
    break_duration: Optional[float] = None
    is_complete: bool = False
    is_weekend: bool = False
    status: str = 'active'  # active, incomplete, complete, break_exceeded

class MonthlyReportQuery(BaseModel):
    year: int
    month: int

# Helper Functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def is_weekend(date_obj: datetime) -> bool:
    return date_obj.weekday() in [5, 6]  # Saturday=5, Sunday=6

def calculate_hours(start: datetime, end: datetime) -> float:
    delta = end - start
    return round(delta.total_seconds() / 3600, 2)

async def send_incomplete_shift_email(employer_email: str, incomplete_employees: List[dict]):
    if not resend.api_key:
        logging.warning("Resend API key not configured. Email not sent.")
        return
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #2563eb;">Daily Attendance Alert</h2>
        <p>The following employees have not completed their 9-hour shift today:</p>
        <table style="border-collapse: collapse; width: 100%; margin-top: 20px;">
            <thead>
                <tr style="background-color: #f3f4f6;">
                    <th style="border: 1px solid #e5e7eb; padding: 12px; text-align: left;">Employee Name</th>
                    <th style="border: 1px solid #e5e7eb; padding: 12px; text-align: left;">Email</th>
                    <th style="border: 1px solid #e5e7eb; padding: 12px; text-align: left;">Hours Worked</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for emp in incomplete_employees:
        html_content += f"""
                <tr>
                    <td style="border: 1px solid #e5e7eb; padding: 12px;">{emp['name']}</td>
                    <td style="border: 1px solid #e5e7eb; padding: 12px;">{emp['email']}</td>
                    <td style="border: 1px solid #e5e7eb; padding: 12px;">{emp['hours']} hours</td>
                </tr>
        """
    
    html_content += """
            </tbody>
        </table>
        <p style="margin-top: 20px; color: #6b7280;">This is an automated alert sent at 9 PM IST.</p>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [employer_email],
            "subject": f"Daily Attendance Alert - {len(incomplete_employees)} Incomplete Shifts",
            "html": html_content
        }
        email = await asyncio.to_thread(resend.Emails.send, params)
        logging.info(f"Email sent to {employer_email}: {email.get('id')}")
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")

async def daily_attendance_check():
    logging.info("Running daily attendance check...")
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    # Get all attendance records for today
    attendance_records = await db.attendance.find(
        {"date": today, "is_weekend": False},
        {"_id": 0}
    ).to_list(1000)
    
    incomplete_employees = []
    
    for record in attendance_records:
        if record.get('punch_in') and record.get('punch_out'):
            total_hours = record.get('total_hours', 0)
            if total_hours < 9:
                incomplete_employees.append({
                    'name': record['user_name'],
                    'email': record['user_email'],
                    'hours': total_hours
                })
        elif record.get('punch_in') and not record.get('punch_out'):
            # Not punched out yet
            incomplete_employees.append({
                'name': record['user_name'],
                'email': record['user_email'],
                'hours': 0
            })
    
    if incomplete_employees:
        # Get all employers
        employers = await db.users.find({"role": "employer"}, {"_id": 0}).to_list(1000)
        
        for employer in employers:
            await send_incomplete_shift_email(employer['email'], incomplete_employees)

# Auth Routes
@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    import uuid
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user_data.password)
    
    user_doc = {
        "user_id": user_id,
        "email": user_data.email,
        "password": hashed_password,
        "name": user_data.name,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_access_token({"sub": user_id, "role": user_data.role})
    
    return {
        "token": token,
        "user": {
            "user_id": user_id,
            "email": user_data.email,
            "name": user_data.name,
            "role": user_data.role
        }
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": user['user_id'], "role": user['role']})
    
    return {
        "token": token,
        "user": {
            "user_id": user['user_id'],
            "email": user['email'],
            "name": user['name'],
            "role": user['role']
        }
    }

# Attendance Routes
@api_router.post("/attendance/punch-in")
async def punch_in(current_user: User = Depends(get_current_user)):
    if current_user.role != 'employee':
        raise HTTPException(status_code=403, detail="Only employees can punch in")
    
    today = datetime.now(timezone.utc).date()
    today_str = today.isoformat()
    
    # Check if already punched in today
    existing = await db.attendance.find_one({"user_id": current_user.user_id, "date": today_str})
    if existing and existing.get('punch_in'):
        raise HTTPException(status_code=400, detail="Already punched in today")
    
    now = datetime.now(timezone.utc)
    is_weekend_day = is_weekend(now)
    
    import uuid
    attendance_id = str(uuid.uuid4())
    
    attendance_doc = {
        "attendance_id": attendance_id,
        "user_id": current_user.user_id,
        "user_name": current_user.name,
        "user_email": current_user.email,
        "date": today_str,
        "punch_in": now.isoformat(),
        "punch_out": None,
        "break_start": None,
        "break_end": None,
        "total_hours": None,
        "break_duration": None,
        "is_complete": False,
        "is_weekend": is_weekend_day,
        "status": "active"
    }
    
    await db.attendance.insert_one(attendance_doc)
    
    return {"message": "Punched in successfully", "punch_in_time": now.isoformat()}

@api_router.post("/attendance/punch-out")
async def punch_out(current_user: User = Depends(get_current_user)):
    if current_user.role != 'employee':
        raise HTTPException(status_code=403, detail="Only employees can punch out")
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    attendance = await db.attendance.find_one({"user_id": current_user.user_id, "date": today})
    if not attendance or not attendance.get('punch_in'):
        raise HTTPException(status_code=400, detail="No active punch-in found for today")
    
    if attendance.get('punch_out'):
        raise HTTPException(status_code=400, detail="Already punched out today")
    
    now = datetime.now(timezone.utc)
    punch_in_time = datetime.fromisoformat(attendance['punch_in'].replace('Z', '+00:00'))
    
    # Calculate total hours
    total_hours = calculate_hours(punch_in_time, now)
    
    # Calculate break duration if break was taken
    break_duration = 0
    if attendance.get('break_start') and attendance.get('break_end'):
        break_start_time = datetime.fromisoformat(attendance['break_start'].replace('Z', '+00:00'))
        break_end_time = datetime.fromisoformat(attendance['break_end'].replace('Z', '+00:00'))
        break_duration = calculate_hours(break_start_time, break_end_time)
    
    # Determine status
    work_hours = total_hours - break_duration
    is_complete = work_hours >= 9
    status = 'complete' if is_complete else 'incomplete'
    
    if break_duration > 1:
        status = 'break_exceeded'
    
    await db.attendance.update_one(
        {"user_id": current_user.user_id, "date": today},
        {"$set": {
            "punch_out": now.isoformat(),
            "total_hours": total_hours,
            "break_duration": break_duration,
            "is_complete": is_complete,
            "status": status
        }}
    )
    
    return {
        "message": "Punched out successfully",
        "total_hours": total_hours,
        "break_duration": break_duration,
        "work_hours": work_hours,
        "is_complete": is_complete
    }

@api_router.post("/attendance/start-break")
async def start_break(current_user: User = Depends(get_current_user)):
    if current_user.role != 'employee':
        raise HTTPException(status_code=403, detail="Only employees can start break")
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    attendance = await db.attendance.find_one({"user_id": current_user.user_id, "date": today})
    if not attendance or not attendance.get('punch_in'):
        raise HTTPException(status_code=400, detail="Must punch in first")
    
    if attendance.get('punch_out'):
        raise HTTPException(status_code=400, detail="Already punched out")
    
    if attendance.get('break_start') and not attendance.get('break_end'):
        raise HTTPException(status_code=400, detail="Break already in progress")
    
    now = datetime.now(timezone.utc)
    
    await db.attendance.update_one(
        {"user_id": current_user.user_id, "date": today},
        {"$set": {"break_start": now.isoformat()}}
    )
    
    return {"message": "Break started", "break_start_time": now.isoformat()}

@api_router.post("/attendance/end-break")
async def end_break(current_user: User = Depends(get_current_user)):
    if current_user.role != 'employee':
        raise HTTPException(status_code=403, detail="Only employees can end break")
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    attendance = await db.attendance.find_one({"user_id": current_user.user_id, "date": today})
    if not attendance or not attendance.get('break_start'):
        raise HTTPException(status_code=400, detail="No active break found")
    
    if attendance.get('break_end'):
        raise HTTPException(status_code=400, detail="Break already ended")
    
    now = datetime.now(timezone.utc)
    
    await db.attendance.update_one(
        {"user_id": current_user.user_id, "date": today},
        {"$set": {"break_end": now.isoformat()}}
    )
    
    return {"message": "Break ended", "break_end_time": now.isoformat()}

@api_router.get("/attendance/my-history", response_model=List[AttendanceRecord])
async def get_my_history(current_user: User = Depends(get_current_user)):
    if current_user.role != 'employee':
        raise HTTPException(status_code=403, detail="Only employees can view their history")
    
    records = await db.attendance.find(
        {"user_id": current_user.user_id},
        {"_id": 0}
    ).sort("date", -1).limit(90).to_list(90)
    
    return records

@api_router.get("/attendance/today-status")
async def get_today_status(current_user: User = Depends(get_current_user)):
    if current_user.role != 'employee':
        raise HTTPException(status_code=403, detail="Only employees can view their status")
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    attendance = await db.attendance.find_one(
        {"user_id": current_user.user_id, "date": today},
        {"_id": 0}
    )
    
    if not attendance:
        return {"has_attendance": False}
    
    return {"has_attendance": True, "attendance": attendance}

@api_router.get("/attendance/all-employees", response_model=List[AttendanceRecord])
async def get_all_employees_attendance(current_user: User = Depends(get_current_user)):
    if current_user.role != 'employer':
        raise HTTPException(status_code=403, detail="Only employers can view all attendance")
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    records = await db.attendance.find(
        {"date": today},
        {"_id": 0}
    ).to_list(1000)
    
    return records

@api_router.post("/attendance/monthly-report", response_model=List[AttendanceRecord])
async def get_monthly_report(query: MonthlyReportQuery, current_user: User = Depends(get_current_user)):
    if current_user.role != 'employer':
        raise HTTPException(status_code=403, detail="Only employers can view monthly reports")
    
    # Create date range for the month
    from calendar import monthrange
    _, last_day = monthrange(query.year, query.month)
    
    start_date = f"{query.year}-{query.month:02d}-01"
    end_date = f"{query.year}-{query.month:02d}-{last_day:02d}"
    
    records = await db.attendance.find(
        {"date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0}
    ).sort("date", -1).to_list(10000)
    
    return records

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Scheduler for daily email at 9 PM IST
scheduler = AsyncIOScheduler()
ist = pytz.timezone('Asia/Kolkata')
scheduler.add_job(
    daily_attendance_check,
    CronTrigger(hour=21, minute=0, timezone=ist),
    id='daily_attendance_check'
)

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    logger.info("Scheduler started - Daily email at 9 PM IST")

@app.on_event("shutdown")
async def shutdown_db_client():
    scheduler.shutdown()
    client.close()
