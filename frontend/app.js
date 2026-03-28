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
const voiceBtn = document.getElementById('voice-btn');
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
let audioRecorderInitialized = false;
let audioPlayerInitialized = false;

// Voice recording state
let isRecording = false;
let currentVoiceMode = null; // 'microphone' or 'voice'
let lastUsedMode = null; // Persists for the turn

// Message tracking
let currentMessageId = null;
let currentBubbleElement = null;
let currentInputTranscriptionElement = null;
let currentOutputTranscriptionElement = null;
let isAgentSpeaking = false;
let typingIndicator = null;
let speechBuffer = '';
let speechRevealInterval = null;

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
    
    typingIndicator = showTyping();
  }
}

// Voice handlers
micBtn.addEventListener('click', () => handleVoiceClick('microphone'));
voiceBtn.addEventListener('click', () => handleVoiceClick('voice'));

async function handleVoiceClick(mode) {
  if (currentVoiceMode && currentVoiceMode !== mode) return;
  
  if (!isRecording) {
    await startRecording(mode);
  } else {
    stopRecording();
  }
}

async function startRecording(mode) {
  clearEmpty();
  currentVoiceMode = mode;
  lastUsedMode = mode;
  
  const needsAudioPlayer = mode === 'voice';
  
  try {
    if (!audioRecorderInitialized) {
      const [recorderNode, recorderCtx, stream] = await startAudioRecorderWorklet(audioRecorderHandler);
      audioRecorderNode = recorderNode;
      audioRecorderContext = recorderCtx;
      micStream = stream;
      audioRecorderInitialized = true;
      console.log('[AUDIO] Audio recorder initialized');
    }
    
    if (needsAudioPlayer && !audioPlayerInitialized) {
      const [playerNode, playerCtx] = await startAudioPlayerWorklet();
      audioPlayerNode = playerNode;
      audioPlayerContext = playerCtx;
      audioPlayerInitialized = true;
      console.log('[AUDIO] Audio player initialized');
    }
    
    setStatus('audio initialized');
  } catch (err) {
    appendMessage('bot', 'Could not start audio. Please check microphone permissions.');
    console.error('Audio initialization error:', err);
    return;
  }
  
  isRecording = true;
  
  if (mode === 'microphone') {
    micBtn.classList.remove('idle');
    micBtn.classList.add('recording');
  } else {
    voiceBtn.classList.remove('idle');
    voiceBtn.classList.add('recording');
  }
  
  voiceBars.classList.remove('hidden');
  setStatus('listening…');
  updateButtonStates();
  
  typingIndicator = showTyping();
}

function stopRecording() {
  isRecording = false;
  currentVoiceMode = null; // Clear active recording, but keep lastUsedMode for response
  
  micBtn.classList.remove('recording');
  micBtn.classList.add('idle');
  voiceBtn.classList.remove('recording');
  voiceBtn.classList.add('idle');
  
  voiceBars.classList.add('hidden');
  setStatus('ready');
  updateButtonStates();
}

function startSpeechReveal() {
  let revealedLength = 0;
  const charsPerSecond = 14;
  const intervalMs = 1000 / charsPerSecond;
  
  speechRevealInterval = setInterval(() => {
    if (revealedLength < speechBuffer.length) {
      revealedLength++;
      const revealed = speechBuffer.substring(0, revealedLength);
      if (currentOutputTranscriptionElement) {
        updateBubble(currentOutputTranscriptionElement, revealed, true);
      }
    } else {
      clearInterval(speechRevealInterval);
      speechRevealInterval = null;
    }
  }, intervalMs);
}

function updateButtonStates() {
  if (isRecording) {
    inputEl.disabled = true;
    
    if (currentVoiceMode === 'microphone') {
      micBtn.title = 'Click to stop';
      voiceBtn.disabled = true;
      voiceBtn.title = 'Stop microphone first';
      sendBtn.disabled = true;
      sendBtn.title = 'Stop recording first';
    } else if (currentVoiceMode === 'voice') {
      voiceBtn.title = 'Click to stop';
      micBtn.disabled = true;
      micBtn.title = 'Stop voice first';
      sendBtn.disabled = true;
      sendBtn.title = 'Stop recording first';
    }
  } else {
    inputEl.disabled = false;
    micBtn.disabled = false;
    micBtn.title = 'Speech to text';
    voiceBtn.disabled = false;
    voiceBtn.title = 'Voice conversation';
    sendBtn.disabled = false;
    sendBtn.title = 'Send message';
  }
}

function audioRecorderHandler(pcmData) {
  if (websocket && websocket.readyState === WebSocket.OPEN && isRecording) {
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
    console.log("[SERVER]", JSON.stringify(adkEvent, null, 2));
    
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
    if (typingIndicator) {
      typingIndicator.remove();
      typingIndicator = null;
    }
    if (speechRevealInterval) {
      clearInterval(speechRevealInterval);
      speechRevealInterval = null;
    }
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
    isAgentSpeaking = false;
    lastUsedMode = null;
    speechBuffer = '';
    
    setStatus('ready');
    return;
  }
  
  // Interrupted - cleanup
  if (event.interrupted) {
    if (typingIndicator) {
      typingIndicator.remove();
      typingIndicator = null;
    }
    if (speechRevealInterval) {
      clearInterval(speechRevealInterval);
      speechRevealInterval = null;
    }
    if (audioPlayerNode) {
      audioPlayerNode.port.postMessage({ command: "endOfAudio" });
    }
    currentMessageId = null;
    currentBubbleElement = null;
    currentInputTranscriptionElement = null;
    currentOutputTranscriptionElement = null;
    isAgentSpeaking = false;
    lastUsedMode = null;
    speechBuffer = '';
    
    setStatus('ready');
    return;
  }
  
  // Input transcription (user speaking) - stream to textarea
  if (event.inputTranscription && event.inputTranscription.text) {
    const text = event.inputTranscription.text;
    const isFinished = event.inputTranscription.finished;
    
    // Stream transcription into textarea
    inputEl.value = text;
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
    
    // When finished, show as user message and auto-send
    if (isFinished) {
      stopRecording();
      clearEmpty();
      appendMessage('user', text);
      inputEl.value = '';
      inputEl.style.height = 'auto';
      // Note: Already sent to backend via audio stream, no need to send again
    }
    return;
  }
  
  // Output transcription (agent speaking)
  if (event.outputTranscription && event.outputTranscription.text) {
    if (typingIndicator) {
      typingIndicator.remove();
      typingIndicator = null;
    }
    
    const text = event.outputTranscription.text;
    const isFinished = event.outputTranscription.finished;
    
    isAgentSpeaking = true;
    setStatus('agent speaking…');
    
    // Voice mode: sync text reveal with audio playback
    if (lastUsedMode === 'voice') {
      speechBuffer = text;
      
      if (!currentOutputTranscriptionElement) {
        currentOutputTranscriptionElement = appendMessage('bot', '', true);
        startSpeechReveal();
      }
      
      if (isFinished) {
        if (speechRevealInterval) {
          clearInterval(speechRevealInterval);
          speechRevealInterval = null;
        }
        updateBubble(currentOutputTranscriptionElement, speechBuffer, false);
        currentOutputTranscriptionElement = null;
        speechBuffer = '';
        isAgentSpeaking = false;
        setStatus('ready');
      }
    } else {
      // Text/microphone mode: show text immediately
      if (!currentOutputTranscriptionElement) {
        currentOutputTranscriptionElement = appendMessage('bot', text, !isFinished);
      } else {
        updateBubble(currentOutputTranscriptionElement, text, !isFinished);
      }
      
      if (isFinished) {
        currentOutputTranscriptionElement = null;
        isAgentSpeaking = false;
        setStatus('ready');
      }
    }
    return;
  }
  
  // Content events
  if (event.content && event.content.parts) {
    if (typingIndicator) {
      typingIndicator.remove();
      typingIndicator = null;
    }
    
    for (const part of event.content.parts) {
      // Audio data (only play in voice mode, not microphone mode)
      if (part.inlineData) {
        const mimeType = part.inlineData.mimeType;
        const data = part.inlineData.data;
        
        if (mimeType && mimeType.startsWith("audio/pcm") && audioPlayerNode && lastUsedMode === 'voice') {
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
connectWebsocket();
inputEl.focus();
