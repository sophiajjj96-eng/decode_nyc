"""FastAPI application with ADK Gemini Live API for NYC civic algorithms."""

import asyncio
import base64
import json
import logging
import warnings
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

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress Pydantic serialization warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Application name constant
APP_NAME = "algorithm-explained"

# ========================================
# Phase 1: Application Initialization (once at startup)
# ========================================

app = FastAPI()

# Mount static files (frontend)
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir, html=True), name="static")

# Define session service
session_service = InMemorySessionService()

# Conversation state storage (keyed by user_id/session_id)
conversation_states: dict[str, ConversationState] = {}

# Define runner
runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)

# ========================================
# HTTP Endpoints
# ========================================


@app.get("/")
async def root():
    """Serve the index.html page."""
    return FileResponse(frontend_dir / "index.html")


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
    proactivity: bool = False,
    affective_dialog: bool = False,
) -> None:
    """WebSocket endpoint for bidirectional streaming with ADK.

    Args:
        websocket: The WebSocket connection
        user_id: User identifier
        session_id: Session identifier
        proactivity: Enable proactive audio (native audio models only)
        affective_dialog: Enable affective dialog (native audio models only)
    """
    logger.debug(
        f"WebSocket connection request: user_id={user_id}, session_id={session_id}, "
        f"proactivity={proactivity}, affective_dialog={affective_dialog}"
    )
    await websocket.accept()
    logger.debug("WebSocket connection accepted")

    # ========================================
    # Phase 2: Session Initialization (once per streaming session)
    # ========================================

    # Automatically determine response modality based on model architecture
    model_name = agent.model
    is_native_audio = isinstance(model_name, str) and "native-audio" in model_name.lower()

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
        conversation_states[state_key] = ConversationState()
        logger.debug(f"Created new conversation state for {state_key}")
    
    conv_state = conversation_states[state_key]

    live_request_queue = LiveRequestQueue()

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
        
        # Send welcome message if this is a new conversation
        if not conv_state.history:
            logger.debug("New conversation detected, sending welcome message")
            welcome_data = get_welcome_message()
            welcome_message = {
                "type": "welcome",
                "message": welcome_data["message"],
                "prompts": welcome_data["prompts"]
            }
            await websocket.send_text(json.dumps(welcome_message))
            logger.debug(f"Sent welcome message with {len(welcome_data['prompts'])} prompts")
        
        # Track assistant response text for follow-up generation
        turn_response_text = ""
        
        async for event in runner.run_live(
            user_id=user_id,
            session_id=session_id,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            # Track assistant messages in conversation state
            if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
                if event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            turn_response_text += part.text
                            conv_state.add_message("assistant", part.text)
                            logger.debug(f"Tracked assistant message: {part.text[:100]}...")
            
            event_json = event.model_dump_json(exclude_none=True, by_alias=True)
            logger.debug(f"[SERVER] Event: {event_json}")
            await websocket.send_text(event_json)
            
            # Generate follow-up questions when turn completes
            if hasattr(event, "turn_complete") and event.turn_complete and turn_response_text:
                logger.debug("Turn completed, generating follow-up questions")
                
                # Convert conversation state to format expected by generator
                history_for_followup = [
                    {"role": msg.role, "text": msg.text}
                    for msg in conv_state.history[-10:]
                ]
                
                followup_questions = await generate_followup_questions(history_for_followup)
                
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
