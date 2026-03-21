from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
from bson import ObjectId
import socketio
from agora_token_builder import RtcTokenBuilder
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# Security
security = HTTPBearer()

# Socket.IO for real-time location updates
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Create the main app
app = FastAPI()

# Socket.IO app
socket_app = socketio.ASGIApp(sio, app)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class UserRegister(BaseModel):
    phone_number: str
    password: str
    name: str

class UserLogin(BaseModel):
    phone_number: str
    password: str

class User(BaseModel):
    id: str
    phone_number: str
    name: str
    created_at: datetime

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    timestamp: Optional[datetime] = None

class Location(BaseModel):
    id: str
    user_id: str
    latitude: float
    longitude: float
    timestamp: datetime

class ConnectionRequest(BaseModel):
    target_phone: str

class Connection(BaseModel):
    id: str
    requester_id: str
    target_id: str
    status: str  # pending, accepted, rejected
    created_at: datetime

class AlarmCreate(BaseModel):
    title: str
    message: str
    trigger_time: datetime

class Alarm(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    trigger_time: datetime
    created_at: datetime

class SOSAlert(BaseModel):
    id: str
    user_id: str
    latitude: float
    longitude: float
    message: Optional[str] = None
    created_at: datetime
    acknowledged: bool = False

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# Authentication endpoints
@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    # Check if user already exists
    existing_user = await db.users.find_one({"phone_number": user_data.phone_number})
    if existing_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    user_dict = {
        "_id": str(uuid.uuid4()),
        "phone_number": user_data.phone_number,
        "password": hashed_password,
        "name": user_data.name,
        "created_at": datetime.utcnow()
    }
    
    await db.users.insert_one(user_dict)
    
    # Create access token
    access_token = create_access_token({"sub": user_dict["_id"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_dict["_id"],
            "phone_number": user_dict["phone_number"],
            "name": user_dict["name"]
        }
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"phone_number": credentials.phone_number})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid phone number or password")
    
    access_token = create_access_token({"sub": user["_id"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["_id"],
            "phone_number": user["phone_number"],
            "name": user["name"]
        }
    }

@api_router.get("/auth/me")
async def get_me(user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user["_id"],
        "phone_number": user["phone_number"],
        "name": user["name"]
    }

# Location endpoints
@api_router.post("/locations")
async def update_location(location: LocationUpdate, user_id: str = Depends(get_current_user)):
    location_dict = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": location.timestamp or datetime.utcnow()
    }
    
    await db.locations.insert_one(location_dict)
    
    # Emit location update via Socket.IO
    await sio.emit('location_update', {
        "user_id": user_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": location_dict["timestamp"].isoformat()
    })
    
    return {"message": "Location updated successfully", "id": location_dict["_id"]}

@api_router.get("/locations/{target_user_id}")
async def get_user_location(target_user_id: str, user_id: str = Depends(get_current_user)):
    # Check if users are connected
    connection = await db.connections.find_one({
        "$or": [
            {"requester_id": user_id, "target_id": target_user_id, "status": "accepted"},
            {"requester_id": target_user_id, "target_id": user_id, "status": "accepted"}
        ]
    })
    
    if not connection and user_id != target_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's location")
    
    # Get latest location
    location = await db.locations.find_one(
        {"user_id": target_user_id},
        sort=[("timestamp", -1)]
    )
    
    if not location:
        raise HTTPException(status_code=404, detail="No location data found")
    
    return {
        "id": location["_id"],
        "user_id": location["user_id"],
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timestamp": location["timestamp"]
    }

@api_router.get("/locations/history/{target_user_id}")
async def get_location_history(
    target_user_id: str,
    limit: int = 100,
    user_id: str = Depends(get_current_user)
):
    # Check if users are connected
    connection = await db.connections.find_one({
        "$or": [
            {"requester_id": user_id, "target_id": target_user_id, "status": "accepted"},
            {"requester_id": target_user_id, "target_id": user_id, "status": "accepted"}
        ]
    })
    
    if not connection and user_id != target_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's location")
    
    locations = await db.locations.find(
        {"user_id": target_user_id}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return [
        {
            "id": loc["_id"],
            "user_id": loc["user_id"],
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "timestamp": loc["timestamp"]
        }
        for loc in locations
    ]

# Connection endpoints
@api_router.post("/connections/request")
async def send_connection_request(request: ConnectionRequest, user_id: str = Depends(get_current_user)):
    # Find target user
    target_user = await db.users.find_one({"phone_number": request.target_phone})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user["_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot connect to yourself")
    
    # Check if connection already exists
    existing = await db.connections.find_one({
        "$or": [
            {"requester_id": user_id, "target_id": target_user["_id"]},
            {"requester_id": target_user["_id"], "target_id": user_id}
        ]
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Connection already exists")
    
    connection_dict = {
        "_id": str(uuid.uuid4()),
        "requester_id": user_id,
        "target_id": target_user["_id"],
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    await db.connections.insert_one(connection_dict)
    
    return {"message": "Connection request sent", "id": connection_dict["_id"]}

@api_router.get("/connections/pending")
async def get_pending_requests(user_id: str = Depends(get_current_user)):
    requests = await db.connections.find({
        "target_id": user_id,
        "status": "pending"
    }).to_list(100)
    
    result = []
    for req in requests:
        requester = await db.users.find_one({"_id": req["requester_id"]})
        result.append({
            "id": req["_id"],
            "requester": {
                "id": requester["_id"],
                "name": requester["name"],
                "phone_number": requester["phone_number"]
            },
            "created_at": req["created_at"]
        })
    
    return result

@api_router.post("/connections/{connection_id}/accept")
async def accept_connection(connection_id: str, user_id: str = Depends(get_current_user)):
    connection = await db.connections.find_one({"_id": connection_id, "target_id": user_id})
    if not connection:
        raise HTTPException(status_code=404, detail="Connection request not found")
    
    await db.connections.update_one(
        {"_id": connection_id},
        {"$set": {"status": "accepted"}}
    )
    
    return {"message": "Connection accepted"}

@api_router.post("/connections/{connection_id}/reject")
async def reject_connection(connection_id: str, user_id: str = Depends(get_current_user)):
    connection = await db.connections.find_one({"_id": connection_id, "target_id": user_id})
    if not connection:
        raise HTTPException(status_code=404, detail="Connection request not found")
    
    await db.connections.update_one(
        {"_id": connection_id},
        {"$set": {"status": "rejected"}}
    )
    
    return {"message": "Connection rejected"}

@api_router.get("/connections")
async def get_connections(user_id: str = Depends(get_current_user)):
    connections = await db.connections.find({
        "$or": [
            {"requester_id": user_id, "status": "accepted"},
            {"target_id": user_id, "status": "accepted"}
        ]
    }).to_list(100)
    
    result = []
    for conn in connections:
        other_user_id = conn["target_id"] if conn["requester_id"] == user_id else conn["requester_id"]
        other_user = await db.users.find_one({"_id": other_user_id})
        
        # Get latest location
        location = await db.locations.find_one(
            {"user_id": other_user_id},
            sort=[("timestamp", -1)]
        )
        
        result.append({
            "id": conn["_id"],
            "user": {
                "id": other_user["_id"],
                "name": other_user["name"],
                "phone_number": other_user["phone_number"]
            },
            "location": {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "timestamp": location["timestamp"]
            } if location else None
        })
    
    return result

# Alarm endpoints
@api_router.post("/alarms")
async def create_alarm(alarm: AlarmCreate, user_id: str = Depends(get_current_user)):
    alarm_dict = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": alarm.title,
        "message": alarm.message,
        "trigger_time": alarm.trigger_time,
        "created_at": datetime.utcnow()
    }
    
    await db.alarms.insert_one(alarm_dict)
    
    return {"message": "Alarm created", "id": alarm_dict["_id"]}

@api_router.get("/alarms")
async def get_alarms(user_id: str = Depends(get_current_user)):
    alarms = await db.alarms.find({"user_id": user_id}).to_list(100)
    
    return [
        {
            "id": alarm["_id"],
            "title": alarm["title"],
            "message": alarm["message"],
            "trigger_time": alarm["trigger_time"],
            "created_at": alarm["created_at"]
        }
        for alarm in alarms
    ]

@api_router.delete("/alarms/{alarm_id}")
async def delete_alarm(alarm_id: str, user_id: str = Depends(get_current_user)):
    result = await db.alarms.delete_one({"_id": alarm_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    return {"message": "Alarm deleted"}

# SOS endpoints
class SOSRequest(BaseModel):
    latitude: float
    longitude: float
    message: Optional[str] = None

@api_router.post("/sos")
async def send_sos_alert(sos_request: SOSRequest, user_id: str = Depends(get_current_user)):
    # Get user info
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create SOS alert
    sos_dict = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "latitude": sos_request.latitude,
        "longitude": sos_request.longitude,
        "message": sos_request.message or "Emergency! Need help!",
        "created_at": datetime.utcnow(),
        "acknowledged": False
    }
    
    await db.sos_alerts.insert_one(sos_dict)
    
    # Get all connected users
    connections = await db.connections.find({
        "$or": [
            {"requester_id": user_id, "status": "accepted"},
            {"target_id": user_id, "status": "accepted"}
        ]
    }).to_list(100)
    
    # Notify all connected users via Socket.IO
    for conn in connections:
        other_user_id = conn["target_id"] if conn["requester_id"] == user_id else conn["requester_id"]
        
        await sio.emit('sos_alert', {
            "alert_id": sos_dict["_id"],
            "user_id": user_id,
            "user_name": user["name"],
            "user_phone": user["phone_number"],
            "latitude": sos_dict["latitude"],
            "longitude": sos_dict["longitude"],
            "message": sos_dict["message"],
            "created_at": sos_dict["created_at"].isoformat()
        }, room=other_user_id)
    
    return {
        "message": "SOS alert sent successfully",
        "id": sos_dict["_id"],
        "notified_users": len(connections)
    }

@api_router.get("/sos")
async def get_sos_alerts(user_id: str = Depends(get_current_user)):
    # Get alerts from connected users
    connections = await db.connections.find({
        "$or": [
            {"requester_id": user_id, "status": "accepted"},
            {"target_id": user_id, "status": "accepted"}
        ]
    }).to_list(100)
    
    connected_user_ids = []
    for conn in connections:
        other_user_id = conn["target_id"] if conn["requester_id"] == user_id else conn["requester_id"]
        connected_user_ids.append(other_user_id)
    
    # Get SOS alerts from connected users (last 24 hours)
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    sos_alerts = await db.sos_alerts.find({
        "user_id": {"$in": connected_user_ids},
        "created_at": {"$gte": one_day_ago}
    }).sort("created_at", -1).to_list(100)
    
    result = []
    for alert in sos_alerts:
        alert_user = await db.users.find_one({"_id": alert["user_id"]})
        result.append({
            "id": alert["_id"],
            "user": {
                "id": alert_user["_id"],
                "name": alert_user["name"],
                "phone_number": alert_user["phone_number"]
            },
            "latitude": alert["latitude"],
            "longitude": alert["longitude"],
            "message": alert["message"],
            "created_at": alert["created_at"],
            "acknowledged": alert["acknowledged"]
        })
    
    return result

@api_router.post("/sos/{alert_id}/acknowledge")
async def acknowledge_sos(alert_id: str, user_id: str = Depends(get_current_user)):
    result = await db.sos_alerts.update_one(
        {"_id": alert_id},
        {"$set": {"acknowledged": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="SOS alert not found")
    
    return {"message": "SOS alert acknowledged"}

@api_router.get("/sos/my-alerts")
async def get_my_sos_alerts(user_id: str = Depends(get_current_user)):
    # Get user's own SOS alerts
    alerts = await db.sos_alerts.find({"user_id": user_id}).sort("created_at", -1).to_list(50)
    
    return [
        {
            "id": alert["_id"],
            "latitude": alert["latitude"],
            "longitude": alert["longitude"],
            "message": alert["message"],
            "created_at": alert["created_at"],
            "acknowledged": alert["acknowledged"]
        }
        for alert in alerts
    ]

# Agora endpoints
class AgoraTokenRequest(BaseModel):
    channel_name: str
    uid: int = 0  # 0 means Agora will assign a random UID

@api_router.post("/agora/token")
async def generate_agora_token(request: AgoraTokenRequest, user_id: str = Depends(get_current_user)):
    app_id = os.environ.get('AGORA_APP_ID')
    app_certificate = os.environ.get('AGORA_APP_CERTIFICATE')
    
    if not app_id or not app_certificate:
        raise HTTPException(status_code=500, detail="Agora credentials not configured")
    
    # Token expires in 1 hour
    expiration_time_in_seconds = 3600
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + expiration_time_in_seconds
    
    # Role: 1 = Publisher (can send and receive), 2 = Subscriber (receive only)
    role = 1  # Publisher
    
    try:
        token = RtcTokenBuilder.buildTokenWithUid(
            app_id,
            app_certificate,
            request.channel_name,
            request.uid,
            role,
            privilege_expired_ts
        )
        
        return {
            "token": token,
            "app_id": app_id,
            "channel_name": request.channel_name,
            "uid": request.uid,
            "expiration": privilege_expired_ts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")

# Socket.IO events
@sio.event
async def connect(sid, environ):
    logging.info(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    logging.info(f"Client disconnected: {sid}")

@sio.event
async def join_room(sid, data):
    user_id = data.get('user_id')
    if user_id:
        await sio.enter_room(sid, user_id)
        logging.info(f"User {user_id} joined room")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
