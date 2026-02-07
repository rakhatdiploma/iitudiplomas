"""WebSocket endpoint for real-time sign detection."""

import json
import asyncio
import httpx
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.hand_detector import HandDetector
from app.services.sign_buffer import SignBuffer
from app.models.gesture_classifier import GestureClassifier
from app.config import settings

websocket_router = APIRouter()

# Active connections and services
active_connections: Dict[str, WebSocket] = {}
hand_detector = HandDetector()
sign_buffer = SignBuffer()
gesture_classifier = GestureClassifier()


@websocket_router.websocket("/ws/sign-detection")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time sign detection."""
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            payload = message.get("payload", {})
            
            if msg_type == "frame":
                await handle_frame(websocket, payload)
                
            elif msg_type == "command":
                await handle_command(websocket, payload)
                
            else:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": f"Unknown message type: {msg_type}"}
                })
                
    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
        if session_id and session_id in active_connections:
            del active_connections[session_id]
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "payload": {"message": str(e)}
            })
        except:
            pass


async def handle_frame(websocket: WebSocket, payload: dict):
    """Process video frame and return detection result."""
    try:
        image_b64 = payload.get("image")
        timestamp = payload.get("timestamp", 0)
        session_id = payload.get("session_id", "default")
        
        if not image_b64:
            await websocket.send_json({
                "type": "detection",
                "payload": {
                    "sign": None,
                    "confidence": 0,
                    "hand_detected": False,
                    "timestamp": timestamp
                }
            })
            return
        
        # Detect hand
        hand_detected, landmarks, handedness, detection_conf = hand_detector.detect(image_b64)
        
        if not hand_detected:
            await websocket.send_json({
                "type": "detection",
                "payload": {
                    "sign": None,
                    "confidence": 0,
                    "hand_detected": False,
                    "timestamp": timestamp
                }
            })
            return
        
        # Normalize landmarks
        normalized_landmarks = hand_detector.normalize_landmarks(landmarks)
        
        # Classify gesture
        sign, confidence = gesture_classifier.classify(normalized_landmarks)
        
        # Add to buffer if valid sign
        if sign and confidence >= settings.CONFIDENCE_THRESHOLD:
            is_new = sign_buffer.add_sign(session_id, sign, confidence)
            
            # Check if we should commit to LLM
            if is_new and sign_buffer.should_commit(session_id):
                sequence = sign_buffer.commit_sequence(session_id)
                await send_to_llm(session_id, sequence)
        
        # Send detection result
        await websocket.send_json({
            "type": "detection",
            "payload": {
                "sign": sign,
                "confidence": confidence,
                "hand_detected": True,
                "landmarks": landmarks if settings.DEBUG else None,
                "timestamp": timestamp
            }
        })
        
    except Exception as e:
        print(f"Frame processing error: {e}")
        await websocket.send_json({
            "type": "error",
            "payload": {"message": f"Processing error: {str(e)}"}
        })


async def handle_command(websocket: WebSocket, payload: dict):
    """Handle start/stop/clear commands."""
    action = payload.get("action")
    session_id = payload.get("session_id", "default")
    
    if action == "start":
        active_connections[session_id] = websocket
        await websocket.send_json({
            "type": "command",
            "payload": {"status": "started", "session_id": session_id}
        })
        
    elif action == "stop":
        if session_id in active_connections:
            del active_connections[session_id]
        await websocket.send_json({
            "type": "command",
            "payload": {"status": "stopped", "session_id": session_id}
        })
        
    elif action == "clear":
        sign_buffer.clear_session(session_id)
        await websocket.send_json({
            "type": "command",
            "payload": {"status": "cleared", "session_id": session_id}
        })


async def send_to_llm(session_id: str, sequence: list):
    """Send sign sequence to LLM service for translation."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.LLM_SERVICE_URL}/api/v1/translate",
                json={
                    "sign_sequence": sequence,
                    "session_id": session_id,
                    "context": ""
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                # Could broadcast to frontend here if needed
                print(f"LLM translation: {result.get('translation')}")
            
    except Exception as e:
        print(f"Failed to send to LLM: {e}")
