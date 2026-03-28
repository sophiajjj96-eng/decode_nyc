"""FastAPI application with ADK Gemini Live API for NYC civic algorithms."""

import asyncio
import base64
import json
import logging
import warnings
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google import genai
from pydantic import BaseModel

# Load environment variables from .env file BEFORE importing agent
load_dotenv(Path(__file__).parent / ".env")

# Import agent after loading environment variables
# pylint: disable=wrong-import-position
from civic_agent.agent import agent  # noqa: E402
from civic_agent.state import ConversationState  # noqa: E402
from civic_agent.conversation_tool import (  # noqa: E402
    resolve_short_reply,
    should_offer_topic_menu,
    build_top_level_categories,
    clean_answer,
    infer_topic_from_question,
    get_welcome_message,
    generate_followup_questions,
)
from civic_agent.friction_detector import analyze_friction, aggregate_friction_stats  # noqa: E402
from civic_agent.demo_interceptor import get_demo_response  # noqa: E402
from api.friction_report import router as friction_router  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress Pydantic serialization warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Application name constant
APP_NAME = "decodenyc"

# ========================================
# Phase 1: Application Initialization (once at startup)
# ========================================

app = FastAPI()

# Mount API routers
app.include_router(friction_router)

# Mount static files (frontend)
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir, html=True), name="static")

# Define session service
session_service = InMemorySessionService()

# Conversation state storage (keyed by user_id/session_id)
conversation_states: dict[str, ConversationState] = {}

# Define runner
runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)

# Question logger (anonymous)
QUESTIONS_LOG_DIR = Path(__file__).parent / "data"
QUESTIONS_LOG_DIR.mkdir(exist_ok=True)
QUESTIONS_LOG_FILE = QUESTIONS_LOG_DIR / "questions_anonymous.jsonl"


def log_question_anonymously(question_text: str, algorithm_context: str | None = None) -> None:
    """Log question without any user identifiers for bias detection.
    
    Args:
        question_text: The question content only
        algorithm_context: Optional algorithm ID if detected
    """
    try:
        log_entry = {
            "question": question_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if algorithm_context:
            log_entry["algorithm"] = algorithm_context
        
        with QUESTIONS_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        logger.debug(f"Logged anonymous question: {question_text[:50]}...")
    except Exception as e:
        logger.error(f"Failed to log question: {e}")

# ========================================
# HTTP Endpoints
# ========================================


@app.get("/")
async def root():
    """Serve the landing page."""
    return FileResponse(frontend_dir / "index.html")


@app.get("/agent")
async def agent_page():
    """Serve the agent chat interface."""
    return FileResponse(frontend_dir / "agent.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True}


# ========================================
# Bias Report Endpoints
# ========================================


class BiasContextRequest(BaseModel):
    """Request model for generating bias report context."""
    conversation_history: list[dict[str, str]]


class BiasContextResponse(BaseModel):
    """Response model for bias report context."""
    title: str
    body: str


class BiasReportRequest(BaseModel):
    """Request model for submitting a bias report."""
    title: str
    body: str
    email: str | None = None
    user_explanation: str


class BiasReportResponse(BaseModel):
    """Response model for bias report submission."""
    success: bool
    summary: str


async def generate_bias_context_with_gemini(
    conversation_history: list[dict[str, str]]
) -> dict[str, str]:
    """Generate title and body for bias report using Gemini.
    
    Args:
        conversation_history: List of conversation messages with role and text
        
    Returns:
        Dictionary with title and body fields
    """
    import os
    
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Format conversation history for prompt
    formatted_history = "\n".join([
        f"{msg['role'].upper()}: {msg['text']}"
        for msg in conversation_history[-10:]
    ])
    
    if not formatted_history:
        formatted_history = "No conversation history available"
    
    prompt = f"""You are reviewing a conversation about NYC government algorithms to help document a potential bias concern.

Conversation history:
{formatted_history}

Generate:
1. A concise title (max 10 words) summarizing the potential bias concern based on the conversation
2. A body (3-5 sentences) providing context about what was discussed in the conversation

Format your response as JSON with this exact structure:
{{"title": "your title here", "body": "your body text here"}}

Important: Return ONLY the JSON object, no other text."""
    
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
        )
        
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        data = json.loads(response_text)
        
        return {
            "title": data.get("title", "Bias Report"),
            "body": data.get("body", "Conversation context unavailable")
        }
        
    except Exception as e:
        logger.error(f"Error generating bias context: {e}")
        return {
            "title": "Bias Report",
            "body": "A conversation about NYC algorithmic tools raised potential bias concerns that warrant review."
        }


@app.post("/api/generate-bias-context")
async def generate_bias_context(request: BiasContextRequest) -> BiasContextResponse:
    """Generate title and body for bias report using Gemini.
    
    Args:
        request: Contains conversation history
        
    Returns:
        Generated title and body for the bias report
    """
    context = await generate_bias_context_with_gemini(request.conversation_history)
    return BiasContextResponse(**context)


@app.post("/api/flag-bias")
async def flag_bias(request: BiasReportRequest) -> BiasReportResponse:
    """Submit a bias report.
    
    Args:
        request: Contains title, body, email, and user explanation
        
    Returns:
        Success status and summary
    """
    logger.info("=" * 80)
    logger.info("BIAS REPORT SUBMITTED")
    logger.info(f"Title: {request.title}")
    logger.info(f"Email: {request.email or 'Not provided'}")
    logger.info(f"Body: {request.body}")
    logger.info(f"User Explanation: {request.user_explanation}")
    logger.info("=" * 80)
    
    summary = f"Report: {request.title}"
    
    return BiasReportResponse(
        success=True,
        summary=summary
    )


# ========================================
# WebSocket Endpoint
# ========================================


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
    language: str = "en",
    proactivity: bool = False,
    affective_dialog: bool = False,
) -> None:
    """WebSocket endpoint for bidirectional streaming with ADK.

    Args:
        websocket: The WebSocket connection
        user_id: User identifier
        session_id: Session identifier
        language: Language code (en, es, zh-CN)
        proactivity: Enable proactive audio (native audio models only)
        affective_dialog: Enable affective dialog (native audio models only)
    """
    logger.debug(
        f"WebSocket connection request: user_id={user_id}, session_id={session_id}, "
        f"language={language}, proactivity={proactivity}, affective_dialog={affective_dialog}"
    )
    await websocket.accept()
    logger.debug("WebSocket connection accepted")

    # ========================================
    # Phase 2: Session Initialization (once per streaming session)
    # ========================================

    # Automatically determine response modality based on model architecture
    model_name = agent.model
    is_native_audio = isinstance(model_name, str) and (
        "native-audio" in model_name.lower() or "flash-live" in model_name.lower()
    )

    if is_native_audio:
        # Native audio models require AUDIO response modality with transcription
        response_modalities = ["AUDIO"]

        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=response_modalities,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=types.SessionResumptionConfig(),
            proactivity=(
                types.ProactivityConfig(proactive_audio=True)
                if proactivity
                else None
            ),
            enable_affective_dialog=affective_dialog
            if affective_dialog
            else None,
        )
        logger.debug(
            f"Native audio model detected: {model_name}, "
            f"using AUDIO response modality, "
            f"proactivity={proactivity}, affective_dialog={affective_dialog}"
        )
    else:
        # Half-cascade models support TEXT response modality
        response_modalities = ["TEXT"]
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=response_modalities,
            input_audio_transcription=None,
            output_audio_transcription=None,
            session_resumption=types.SessionResumptionConfig(),
        )
        logger.debug(
            f"Half-cascade model detected: {model_name}, "
            "using TEXT response modality"
        )
        if proactivity or affective_dialog:
            logger.warning(
                f"Proactivity and affective dialog are only supported on native "
                f"audio models. Current model: {model_name}. "
                f"These settings will be ignored."
            )
    logger.debug(f"RunConfig created: {run_config}")

    # Get or create session
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if not session:
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
    
    # Initialize conversation state for this session
    state_key = f"{user_id}:{session_id}"
    if state_key not in conversation_states:
        conversation_states[state_key] = ConversationState(language=language)
        logger.debug(f"Created new conversation state for {state_key} with language={language}")
    
    conv_state = conversation_states[state_key]
    
    # Send welcome message if this is a new conversation
    if not conv_state.history:
        logger.debug("New conversation detected, sending welcome message")
        welcome_data = get_welcome_message(conv_state.language)
        welcome_message = {
            "type": "welcome",
            "message": welcome_data["message"],
            "prompts": welcome_data["prompts"]
        }
        await websocket.send_text(json.dumps(welcome_message))
        logger.debug(f"Sent welcome message with {len(welcome_data['prompts'])} prompts")

    live_request_queue = LiveRequestQueue()
    
    # Shared state for demo interception
    demo_state = {
        "question": None,
        "response_data": None,
        "response_sent": False
    }

    # ========================================
    # Phase 3: Active Session (concurrent bidirectional communication)
    # ========================================

    async def upstream_task() -> None:
        """Receives messages from WebSocket and sends to LiveRequestQueue."""
        logger.debug("upstream_task started")
        while True:
            message = await websocket.receive()

            # Handle binary frames (audio data)
            if "bytes" in message:
                audio_data = message["bytes"]
                logger.debug(
                    f"Received binary audio chunk: {len(audio_data)} bytes"
                )

                audio_blob = types.Blob(
                    mime_type="audio/pcm;rate=16000", data=audio_data
                )
                live_request_queue.send_realtime(audio_blob)

            # Handle text frames (JSON messages)
            elif "text" in message:
                text_data = message["text"]
                logger.debug(f"Received text message: {text_data[:100]}...")

                json_message = json.loads(text_data)

                # Extract text from JSON and send to LiveRequestQueue
                if json_message.get("type") == "text":
                    user_text = json_message["text"]
                    logger.debug(f"Sending text content: {user_text}")
                    
                    # Track user message in conversation state
                    conv_state.add_message("user", user_text)
                    
                    # Log question anonymously (no user identifiers)
                    algo_context = infer_topic_from_question(user_text)
                    log_question_anonymously(user_text, algo_context)
                    
                    # Analyze for friction/skepticism signals (Social Antenna)
                    friction_analysis = await analyze_friction(user_text)
                    if friction_analysis.get("is_high_friction"):
                        logger.info(
                            f"HIGH FRICTION detected: score={friction_analysis['friction_score']}, "
                            f"sentiment={friction_analysis['sentiment']}, "
                            f"algo={friction_analysis.get('algorithm_id', 'unknown')}"
                        )
                    
                    # Resolve short replies like "1", "first", "both"
                    resolved_text = resolve_short_reply(
                        question=user_text,
                        last_options=conv_state.last_options,
                        current_topic=conv_state.current_topic,
                    )
                    
                    # If text was resolved, update it
                    if resolved_text != user_text:
                        logger.debug(f"Resolved '{user_text}' to '{resolved_text}'")
                        user_text = resolved_text
                    
                    # Check for demo question and store for interception
                    demo_response_data = get_demo_response(user_text)
                    demo_state["question"] = user_text
                    demo_state["response_data"] = demo_response_data
                    demo_state["response_sent"] = False
                    
                    if demo_response_data:
                        logger.info(f"Demo question detected: {demo_response_data['demo_id']}")
                    
                    # Always send to AI (we'll intercept the response)
                    content = types.Content(
                        parts=[types.Part(text=user_text)]
                    )
                    live_request_queue.send_content(content)

    async def downstream_task() -> None:
        """Receives Events from run_live() and sends to WebSocket."""
        logger.debug("downstream_task started, calling runner.run_live()")
        logger.debug(
            f"Starting run_live with user_id={user_id}, session_id={session_id}"
        )
        
        # Track assistant response text for follow-up generation
        turn_response_text = ""
        
        async for event in runner.run_live(
            user_id=user_id,
            session_id=session_id,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            # Check if demo interception is needed
            if demo_state["response_data"] and not demo_state["response_sent"]:
                demo_data = demo_state["response_data"]
                logger.info(f"Intercepting with demo response: {demo_data['demo_id']}")
                
                # Send hard-coded response in ADK-compatible format
                response_text = demo_data["response"]
                chunk_size = 50
                
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i + chunk_size]
                    # Use ADK event format so frontend handles it correctly
                    content_event = {
                        "content": {
                            "parts": [{"text": chunk}]
                        },
                        "partial": True,
                        "invocationId": "demo",
                        "author": "model",
                        "actions": [],
                        "id": f"demo-{i}",
                        "timestamp": ""
                    }
                    await websocket.send_text(json.dumps(content_event))
                    await asyncio.sleep(0.02)
                
                # Track in conversation state
                conv_state.add_message("assistant", response_text)
                
                # Send turn complete
                complete_event = {"turnComplete": True}
                await websocket.send_text(json.dumps(complete_event))
                
                # Send hard-coded follow-up questions
                if demo_data.get("followup_questions"):
                    followup_message = {
                        "type": "suggested_prompts",
                        "prompts": demo_data["followup_questions"]
                    }
                    await websocket.send_text(json.dumps(followup_message))
                    logger.debug(f"Sent {len(demo_data['followup_questions'])} demo follow-ups")
                
                # Mark as sent
                demo_state["response_sent"] = True
                
                # Skip this AI event
                continue
            
            # If demo response was sent, suppress remaining AI events until turn complete
            if demo_state["response_sent"]:
                if hasattr(event, "turn_complete") and event.turn_complete:
                    logger.debug("AI turn complete after demo, resetting state")
                    demo_state["question"] = None
                    demo_state["response_data"] = None
                    demo_state["response_sent"] = False
                continue
            
            # Normal AI flow - track assistant messages in conversation state
            if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
                if event.content.parts:
                    for part in event.content.parts:
                        # Filter out thought parts
                        is_thought = hasattr(part, "thought") and part.thought
                        if hasattr(part, "text") and part.text and not is_thought:
                            turn_response_text += part.text
                            conv_state.add_message("assistant", part.text)
                            logger.debug(f"Tracked assistant message: {part.text[:100]}...")
            
            event_json = event.model_dump_json(exclude_none=True, by_alias=True)
            logger.debug(f"[SERVER] Event: {event_json}")
            await websocket.send_text(event_json)
            
            # Generate follow-up questions when turn completes
            if hasattr(event, "turn_complete") and event.turn_complete:
                if turn_response_text:
                    logger.debug("Turn completed, generating follow-up questions")
                    
                    # Convert conversation state to format expected by generator
                    history_for_followup = [
                        {"role": msg.role, "text": msg.text}
                        for msg in conv_state.history[-10:]
                    ]
                    
                    followup_questions = await generate_followup_questions(
                        history_for_followup, 
                        conv_state.language
                    )
                    
                    if followup_questions:
                        logger.debug(f"Generated {len(followup_questions)} follow-up questions")
                        followup_message = {
                            "type": "suggested_prompts",
                            "prompts": followup_questions
                        }
                        await websocket.send_text(json.dumps(followup_message))
                    else:
                        logger.debug("No follow-up questions generated")
                
                # Reset for next turn
                turn_response_text = ""
        
        logger.debug("run_live() generator completed")

    # Run both tasks concurrently
    try:
        logger.debug(
            "Starting asyncio.gather for upstream and downstream tasks"
        )
        await asyncio.gather(upstream_task(), downstream_task())
        logger.debug("asyncio.gather completed normally")
    except WebSocketDisconnect:
        logger.debug("Client disconnected normally")
    except Exception as e:
        logger.error(f"Unexpected error in streaming tasks: {e}", exc_info=True)
    finally:
        # ========================================
        # Phase 4: Session Termination
        # ========================================

        logger.debug("Closing live_request_queue")
        live_request_queue.close()
