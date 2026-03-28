/**
 * WebSocket client for Algorithm Explained with ADK bi-directional streaming
 */

import { startAudioPlayerWorklet } from "./audio-player.js";
import { startAudioRecorderWorklet, stopMicrophone } from "./audio-recorder.js";

// DOM Elements
const chat = document.getElementById('chat');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send');
const micBtn = document.getElementById('mic-btn');
const micLabel = document.getElementById('mic-label');
const voiceBars = document.getElementById('voice-bars');
const statusLabel = document.getElementById('status-label');
let empty = document.getElementById('empty');

// WebSocket state
const userId = "civic-user";
const sessionId = "session-" + Math.random().toString(36).substring(7);
let websocket = null;

// Audio state
let audioPlayerNode = null;
let audioPlayerContext = null;
let audioRecorderNode = null;
let audioRecorderContext = null;
let micStream = null;
let audioMode = false;

// Current mode
let currentMode = 'text';
let voiceState = 'idle';

// Message tracking
let currentMessageId = null;
let currentBubbleElement = null;
let currentInputTranscriptionElement = null;
let currentOutputTranscriptionElement = null;

// Mode switching
window.setMode = function(mode) {
  currentMode = mode;
  document.getElementById('text-input-area').classList.toggle('hidden', mode !== 'text');
  document.getElementById('voice-input-area').classList.toggle('hidden', mode !== 'voice');
  document.getElementById('btn-text').classList.toggle('active', mode === 'text');
  document.getElementById('btn-voice').classList.toggle('active', mode === 'voice');
  setStatus('ready');
  if (mode === 'text') inputEl.focus();
};

function setStatus(s) { 
  statusLabel.textContent = s; 
}

function clearEmpty() {
  if (empty) { 
    empty.remove(); 
    empty = null; 
  }
}

// Text input handlers
inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
});

inputEl.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitText();
  }
});

sendBtn.addEventListener('click', submitText);

function submitText() {
  const text = inputEl.value.trim();
  if (!text) return;
  
  clearEmpty();
  appendMessage('user', text);
  inputEl.value = '';
  inputEl.style.height = 'auto';
  
  sendMessage(text);
}

function sendMessage(text) {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    const jsonMessage = JSON.stringify({
      type: "text",
      text: text
    });
    websocket.send(jsonMessage);
    console.log("[CLIENT] Sent text:", text);
  }
}

// Voice handlers
micBtn.addEventListener('click', handleMicClick);

function handleMicClick() {
  if (voiceState === 'idle') startVoiceSession();
  else stopVoiceSession();
}

function setVoiceState(state) {
  voiceState = state;
  
  micBtn.classList.remove('idle', 'listening', 'speaking');
  micBtn.classList.add(state);
  
  if (state === 'idle') {
    micLabel.textContent = 'Start Discussion';
    voiceBars.classList.add('hidden');
    setStatus('ready');
  } else if (state === 'listening') {
    micLabel.textContent = 'Tap to stop';
    voiceBars.classList.remove('hidden');
    setStatus('listening…');
  } else if (state === 'speaking') {
    micLabel.textContent = 'Tap to interrupt';
    voiceBars.classList.remove('hidden');
    setStatus('agent speaking…');
  }
}

async function startVoiceSession() {
  clearEmpty();
  
  if (!audioMode) {
    try {
      await startAudio();
      audioMode = true;
      setStatus('audio initialized');
    } catch (err) {
      appendMessage('bot', 'Could not start audio. Please check microphone permissions.');
      console.error('Audio initialization error:', err);
      return;
    }
  }
  
  setVoiceState('listening');
}

function stopVoiceSession() {
  setVoiceState('idle');
}

async function startAudio() {
  const [playerNode, playerCtx] = await startAudioPlayerWorklet();
  audioPlayerNode = playerNode;
  audioPlayerContext = playerCtx;
  
  const [recorderNode, recorderCtx, stream] = await startAudioRecorderWorklet(audioRecorderHandler);
  audioRecorderNode = recorderNode;
  audioRecorderContext = recorderCtx;
  micStream = stream;
  
  console.log('[AUDIO] Audio worklets started');
}

function audioRecorderHandler(pcmData) {
  if (websocket && websocket.readyState === WebSocket.OPEN && audioMode) {
    websocket.send(pcmData);
  }
}

// Message rendering
function appendMessage(role, text, streaming = false) {
  const row = document.createElement('div');
  row.className = `row ${role}`;
  
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? 'You' : 'AI';
  
  const bubble = document.createElement('div');
  bubble.className = 'bubble' + (streaming ? ' streaming' : '');
  bubble.textContent = text;
  
  row.appendChild(avatar);
  row.appendChild(bubble);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

function showTyping() {
  const row = document.createElement('div');
  row.className = 'row bot';
  
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = 'AI';
  
  const bubble = document.createElement('div');
  bubble.className = 'bubble typing-bubble';
  bubble.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
  
  row.appendChild(avatar);
  row.appendChild(bubble);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

function updateBubble(element, text, streaming = false) {
  const bubble = element.querySelector('.bubble');
  bubble.textContent = text;
  bubble.className = 'bubble' + (streaming ? ' streaming' : '');
  chat.scrollTop = chat.scrollHeight;
}

// WebSocket connection
function connectWebsocket() {
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = wsProtocol + "//" + window.location.host + "/ws/" + userId + "/" + sessionId;
  
  websocket = new WebSocket(wsUrl);
  
  websocket.onopen = function() {
    console.log("[WEBSOCKET] Connected");
    setStatus('connected');
  };
  
  websocket.onmessage = function(event) {
    const adkEvent = JSON.parse(event.data);
    console.log("[SERVER]", adkEvent);
    
    handleADKEvent(adkEvent);
  };
  
  websocket.onclose = function() {
    console.log("[WEBSOCKET] Closed");
    setStatus('reconnecting…');
    setTimeout(connectWebsocket, 5000);
  };
  
  websocket.onerror = function(e) {
    console.error("[WEBSOCKET] Error:", e);
    setStatus('error');
  };
}

// Handle ADK events
function handleADKEvent(event) {
  // Turn complete - reset state
  if (event.turnComplete) {
    if (currentBubbleElement) {
      updateBubble(currentBubbleElement, currentBubbleElement.querySelector('.bubble').textContent, false);
    }
    if (currentOutputTranscriptionElement) {
      updateBubble(currentOutputTranscriptionElement, currentOutputTranscriptionElement.querySelector('.bubble').textContent, false);
    }
    currentMessageId = null;
    currentBubbleElement = null;
    currentInputTranscriptionElement = null;
    currentOutputTranscriptionElement = null;
    
    if (voiceState === 'speaking') {
      setVoiceState('listening');
    }
    return;
  }
  
  // Interrupted - cleanup
  if (event.interrupted) {
    if (audioPlayerNode) {
      audioPlayerNode.port.postMessage({ command: "endOfAudio" });
    }
    currentMessageId = null;
    currentBubbleElement = null;
    currentInputTranscriptionElement = null;
    currentOutputTranscriptionElement = null;
    
    if (voiceState === 'speaking') {
      setVoiceState('listening');
    }
    return;
  }
  
  // Input transcription (user speaking)
  if (event.inputTranscription && event.inputTranscription.text) {
    const text = event.inputTranscription.text;
    const isFinished = event.inputTranscription.finished;
    
    if (!currentInputTranscriptionElement) {
      currentInputTranscriptionElement = appendMessage('user', text, !isFinished);
    } else {
      updateBubble(currentInputTranscriptionElement, text, !isFinished);
    }
    
    if (isFinished) {
      currentInputTranscriptionElement = null;
    }
    return;
  }
  
  // Output transcription (agent speaking)
  if (event.outputTranscription && event.outputTranscription.text) {
    const text = event.outputTranscription.text;
    const isFinished = event.outputTranscription.finished;
    
    if (voiceState === 'listening') {
      setVoiceState('speaking');
    }
    
    if (!currentOutputTranscriptionElement) {
      currentOutputTranscriptionElement = appendMessage('bot', text, !isFinished);
    } else {
      updateBubble(currentOutputTranscriptionElement, text, !isFinished);
    }
    
    if (isFinished) {
      currentOutputTranscriptionElement = null;
    }
    return;
  }
  
  // Content events
  if (event.content && event.content.parts) {
    for (const part of event.content.parts) {
      // Audio data
      if (part.inlineData) {
        const mimeType = part.inlineData.mimeType;
        const data = part.inlineData.data;
        
        if (mimeType && mimeType.startsWith("audio/pcm") && audioPlayerNode) {
          audioPlayerNode.port.postMessage(base64ToArray(data));
        }
      }
      
      // Text data (only if no transcription is handling it)
      if (part.text && !part.thought && !currentOutputTranscriptionElement) {
        if (!currentBubbleElement) {
          currentMessageId = Math.random().toString(36).substring(7);
          currentBubbleElement = appendMessage('bot', part.text, true);
        } else {
          const existingText = currentBubbleElement.querySelector('.bubble').textContent;
          updateBubble(currentBubbleElement, existingText + part.text, true);
        }
      }
    }
  }
}

// Decode base64 to ArrayBuffer
function base64ToArray(base64) {
  let standardBase64 = base64.replace(/-/g, '+').replace(/_/g, '/');
  while (standardBase64.length % 4) {
    standardBase64 += '=';
  }
  
  const binaryString = window.atob(standardBase64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

// Initialize
setMode('text');
connectWebsocket();
