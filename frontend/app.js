/**
 * WebSocket client for DecodeNYC with ADK bi-directional streaming
 */

import { startAudioPlayerWorklet } from "./audio-player.js";
import { startAudioRecorderWorklet, stopMicrophone } from "./audio-recorder.js";
import { injectFlowchartIfNeeded } from "./flowchart-display.js";
import { t, getFlag, getSupportedLanguages } from "./translations.js";

// Language state
let currentLanguage = localStorage.getItem('decodenyc-language') || 'en';
let sessionLanguage = currentLanguage; // Immutable language for current chat session

// DOM Elements
const chat = document.getElementById('chat');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send');
const micBtn = document.getElementById('mic-btn');
const voiceBtn = document.getElementById('voice-btn');
const voiceBars = document.getElementById('voice-bars');
const statusLabel = document.getElementById('status-indicator');
const languageSelector = document.getElementById('language-selector');
const languageDropdown = document.getElementById('language-dropdown');
const currentFlag = document.getElementById('current-flag');
let empty = document.getElementById('empty');

// WebSocket state
const userId = "civic-user";
let sessionId = "session-" + Math.random().toString(36).substring(7);
let websocket = null;
let welcomeReceived = false;

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
let inVoiceSession = false; // Persistent across turns for continuous voice conversation

// Message tracking
let currentMessageId = null;
let currentBubbleElement = null;
let currentInputTranscriptionElement = null;
let currentOutputTranscriptionElement = null;
let isAgentSpeaking = false;
let typingIndicator = null;
let speechBuffer = '';
let speechRevealInterval = null;

// Conversation state (mirrors backend state management)
let conversationHistory = [];
let lastOptions = [];
let currentTopic = null;
let currentSubtopic = null;
let clarificationDepth = 0;

function setStatus(s) {
  const statusColors = {
    'ready': 'green',
    'connected': 'green',
    'audio initialized': 'green',
    'audio mode active': 'green',
    'listening…': 'orange',
    'agent speaking…': 'orange',
    'reconnecting…': 'orange',
    'error': 'red'
  };
  
  const color = statusColors[s] || 'green';
  
  statusLabel.className = 'status-indicator';
  if (color === 'orange') {
    statusLabel.classList.add('status-orange');
  } else if (color === 'red') {
    statusLabel.classList.add('status-red');
  }
}

function clearEmpty() {
  if (empty) { 
    empty.remove(); 
    empty = null; 
  }
}

// Language management
function applyTranslations() {
  // Update input placeholder
  inputEl.placeholder = t('inputPlaceholder', currentLanguage);
  
  // Update button titles
  sendBtn.title = t('sendMessage', currentLanguage);
  micBtn.title = t('speechToText', currentLanguage);
  voiceBtn.title = inVoiceSession ? t('disableAudioMode', currentLanguage) : t('enableAudioMode', currentLanguage);
  
  // Update header button titles
  document.getElementById('new-conversation-btn').title = t('newConversation', currentLanguage);
  document.getElementById('flag-bias-btn').title = t('flagBias', currentLanguage);
  
  // Update empty state
  if (empty) {
    const emptyP = empty.querySelector('p');
    if (emptyP) {
      emptyP.textContent = t('emptyState', currentLanguage);
    }
  }
  
  // Update modal labels
  const modalTitle = document.querySelector('#bias-modal .modal-header h2');
  if (modalTitle) modalTitle.textContent = t('modalTitle', currentLanguage);
  
  const labels = {
    'bias-title': 'issueSummary',
    'bias-email': 'contactEmail',
    'bias-body': 'conversationContext',
    'bias-explanation': 'yourExplanation'
  };
  
  for (const [inputId, key] of Object.entries(labels)) {
    const label = document.querySelector(`label[for="${inputId}"]`);
    if (label) {
      const optionalSpan = label.querySelector('.optional');
      label.textContent = t(key, currentLanguage);
      if (optionalSpan && key === 'contactEmail') {
        label.appendChild(document.createTextNode(' '));
        label.appendChild(optionalSpan);
        optionalSpan.textContent = t('optional', currentLanguage);
      }
    }
  }
  
  const biasExplanation = document.getElementById('bias-explanation');
  if (biasExplanation) {
    biasExplanation.placeholder = t('explanationPlaceholder', currentLanguage);
  }
  
  const discardBtn = document.getElementById('discard-btn');
  if (discardBtn) discardBtn.textContent = t('discard', currentLanguage);
  
  const submitBiasBtn = document.getElementById('submit-bias-btn');
  if (submitBiasBtn && submitBiasBtn.textContent !== t('submitting', currentLanguage)) {
    submitBiasBtn.textContent = t('submit', currentLanguage);
  }
  
  const apologyP = document.querySelector('.apology');
  if (apologyP) apologyP.textContent = t('apology', currentLanguage);
  
  const emailResponseP = document.getElementById('email-response');
  if (emailResponseP) emailResponseP.textContent = t('emailResponse', currentLanguage);
  
  const modalLoadingP = document.querySelector('.modal-loading p');
  if (modalLoadingP) modalLoadingP.textContent = t('generatingContext', currentLanguage);
}

function setLanguage(lang) {
  currentLanguage = lang;
  localStorage.setItem('decodenyc-language', lang);
  currentFlag.textContent = getFlag(lang);
  
  // Update active state in dropdown
  document.querySelectorAll('.language-option').forEach(option => {
    if (option.dataset.lang === lang) {
      option.classList.add('active');
    } else {
      option.classList.remove('active');
    }
  });
  
  // Apply translations
  applyTranslations();
}

// Language selector event handlers
languageSelector.addEventListener('click', (e) => {
  e.stopPropagation();
  languageDropdown.classList.toggle('hidden');
});

document.addEventListener('click', (e) => {
  if (!languageSelector.contains(e.target)) {
    languageDropdown.classList.add('hidden');
  }
});

document.querySelectorAll('.language-option').forEach(option => {
  option.addEventListener('click', (e) => {
    e.stopPropagation();
    const lang = option.dataset.lang;
    
    // If language is different from current session language, start new conversation
    if (lang !== sessionLanguage) {
      // Update the language setting
      setLanguage(lang);
      // Start new conversation with the new language
      resetConversation();
    }
    
    languageDropdown.classList.add('hidden');
  });
});

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
  
  // Track user message in local history
  conversationHistory.push({ role: 'user', text: text });
  
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
voiceBtn.addEventListener('click', () => handleVoiceToggle());

async function handleVoiceToggle() {
  if (inVoiceSession) {
    // End voice session
    endVoiceSession();
  } else {
    // Start voice session (initialize audio without recording)
    await startVoiceSession();
  }
}

async function startVoiceSession() {
  clearEmpty();
  inVoiceSession = true;
  lastUsedMode = 'voice';
  
  try {
    // Initialize audio player for output
    if (!audioPlayerInitialized) {
      const [playerNode, playerCtx] = await startAudioPlayerWorklet();
      audioPlayerNode = playerNode;
      audioPlayerContext = playerCtx;
      audioPlayerInitialized = true;
      console.log('[AUDIO] Audio player initialized for voice session');
    }
    
    // Initialize audio recorder for input
    if (!audioRecorderInitialized) {
      const [recorderNode, recorderCtx, stream] = await startAudioRecorderWorklet(audioRecorderHandler);
      audioRecorderNode = recorderNode;
      audioRecorderContext = recorderCtx;
      micStream = stream;
      audioRecorderInitialized = true;
      console.log('[AUDIO] Audio recorder initialized for voice session');
    }
    
    voiceBtn.classList.remove('idle');
    voiceBtn.classList.add('active');
    setStatus('audio mode active');
    console.log('[AUDIO] Voice session started - type or speak to get audio responses');
  } catch (err) {
    appendMessage('bot', t('audioPermissionError', currentLanguage));
    console.error('Audio initialization error:', err);
    inVoiceSession = false;
    return;
  }
}

async function handleVoiceClick(mode) {
  if (currentVoiceMode && currentVoiceMode !== mode) return;
  
  if (!isRecording) {
    await startRecording(mode);
  } else {
    // Explicitly stopping - end voice session if active
    if (inVoiceSession) {
      endVoiceSession();
    } else {
      stopRecording();
    }
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
    appendMessage('bot', t('audioPermissionError', currentLanguage));
    console.error('Audio initialization error:', err);
    return;
  }
  
  isRecording = true;
  
  if (mode === 'microphone') {
    micBtn.classList.remove('idle');
    micBtn.classList.add('recording');
  }
  
  voiceBars.classList.remove('hidden');
  setStatus('listening…');
  updateButtonStates();
  
  typingIndicator = showTyping();
}

function stopRecording() {
  isRecording = false;
  currentVoiceMode = null;
  
  if (micStream) {
    stopMicrophone(micStream);
    micStream = null;
  }
  
  if (audioRecorderNode) {
    audioRecorderNode.disconnect();
    audioRecorderNode = null;
  }
  
  if (audioRecorderContext) {
    audioRecorderContext.close();
    audioRecorderContext = null;
  }
  
  audioRecorderInitialized = false;
  
  micBtn.classList.remove('recording');
  micBtn.classList.add('idle');
  
  voiceBars.classList.add('hidden');
  setStatus('ready');
  updateButtonStates();
}

function endVoiceSession() {
  inVoiceSession = false;
  isRecording = false;
  currentVoiceMode = null;
  lastUsedMode = null;
  
  if (micStream) {
    stopMicrophone(micStream);
    micStream = null;
  }
  
  if (audioRecorderNode) {
    audioRecorderNode.disconnect();
    audioRecorderNode = null;
  }
  
  if (audioRecorderContext) {
    audioRecorderContext.close();
    audioRecorderContext = null;
  }
  
  if (audioPlayerNode) {
    audioPlayerNode.port.postMessage({ command: "endOfAudio" });
    audioPlayerNode.disconnect();
    audioPlayerNode = null;
  }
  
  if (audioPlayerContext) {
    audioPlayerContext.close();
    audioPlayerContext = null;
  }
  
  audioRecorderInitialized = false;
  audioPlayerInitialized = false;
  
  micBtn.classList.remove('recording');
  micBtn.classList.add('idle');
  voiceBtn.classList.remove('active', 'recording');
  voiceBtn.classList.add('idle');
  
  voiceBars.classList.add('hidden');
  setStatus('ready');
  updateButtonStates();
  
  console.log('[AUDIO] Voice session ended, all audio contexts closed');
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
      micBtn.title = t('stopRecording', currentLanguage);
      voiceBtn.disabled = true;
      voiceBtn.title = t('stopMicFirst', currentLanguage);
      sendBtn.disabled = true;
      sendBtn.title = t('stopRecordingFirst', currentLanguage);
    }
  } else if (inVoiceSession) {
    // Audio mode active but not recording
    inputEl.disabled = false;
    micBtn.disabled = false;
    micBtn.title = t('speechToText', currentLanguage);
    voiceBtn.disabled = false;
    voiceBtn.title = t('disableAudioMode', currentLanguage);
    sendBtn.disabled = false;
    sendBtn.title = t('sendMessage', currentLanguage);
  } else {
    inputEl.disabled = false;
    micBtn.disabled = false;
    micBtn.title = t('speechToText', currentLanguage);
    voiceBtn.disabled = false;
    voiceBtn.title = t('enableAudioMode', currentLanguage);
    sendBtn.disabled = false;
    sendBtn.title = t('sendMessage', currentLanguage);
  }
}

function audioRecorderHandler(pcmData) {
  if (websocket && websocket.readyState === WebSocket.OPEN && (isRecording || inVoiceSession)) {
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
  
  // Ensure text is a string
  const textContent = String(text || '');
  
  // Render markdown for bot messages if marked.js is available
  if (role === 'bot' && window.marked && textContent) {
    try {
      bubble.innerHTML = marked.parse(textContent);
    } catch (err) {
      console.error('[MARKDOWN] Parse error:', err);
      bubble.textContent = textContent;
    }
  } else {
    bubble.textContent = textContent;
  }
  
  row.appendChild(avatar);
  row.appendChild(bubble);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

function renderPromptButtons(prompts, container) {
  if (!prompts || prompts.length === 0) return;
  
  const buttonContainer = document.createElement('div');
  buttonContainer.className = 'category-buttons';
  
  prompts.forEach(prompt => {
    const btn = document.createElement('button');
    btn.className = 'category-btn';
    btn.textContent = prompt;
    btn.onclick = () => {
      clearEmpty();
      appendMessage('user', prompt);
      conversationHistory.push({ role: 'user', text: prompt });
      inputEl.value = '';
      inputEl.style.height = 'auto';
      sendMessage(prompt);
      
      // Remove all prompt buttons after click
      document.querySelectorAll('.category-buttons').forEach(el => el.remove());
    };
    buttonContainer.appendChild(btn);
  });
  
  container.appendChild(buttonContainer);
  chat.scrollTop = chat.scrollHeight;
}

function renderAssistantResponse(text) {
  // Track assistant message in history
  conversationHistory.push({ role: 'assistant', text: text });
  
  // Check if response contains numbered options
  const optionPattern = /^\d+\.\s+(.+)$/gm;
  const matches = [...text.matchAll(optionPattern)];
  
  if (matches.length >= 2) {
    // Extract options
    lastOptions = matches.map(m => m[1].trim());
    clarificationDepth++;
    
    // Try to infer topic from the text
    const lowerText = text.toLowerCase();
    if (!currentTopic) {
      if (lowerText.includes('housing') || lowerText.includes('homeless')) {
        currentTopic = 'Housing and homelessness';
      } else if (lowerText.includes('education') || lowerText.includes('school')) {
        currentTopic = 'Education and schools';
      } else if (lowerText.includes('police') || lowerText.includes('public safety')) {
        currentTopic = 'Public safety and policing';
      } else if (lowerText.includes('child') || lowerText.includes('family')) {
        currentTopic = 'Child welfare and family services';
      }
    }
    
    // Add clickable follow-up buttons if this looks like a follow-up question list
    if (currentBubbleElement && (lowerText.includes('follow-up') || lowerText.includes('question') || matches.length <= 5)) {
      setTimeout(() => {
        addFollowUpButtons(currentBubbleElement, lastOptions);
      }, 300);
    }
  } else {
    // Reset depth when getting specific answer
    clarificationDepth = 0;
  }
  
  // Detect algorithm explanations and inject flowchart
  if (currentBubbleElement) {
    setTimeout(async () => {
      try {
        await injectFlowchartIfNeeded(currentBubbleElement, text);
      } catch (error) {
        console.error('[FLOWCHART] Injection error:', error);
      }
    }, 500);
  }
}

function addFollowUpButtons(messageElement, questions) {
  // Check if buttons already exist
  if (messageElement.querySelector('.category-buttons')) {
    return;
  }
  
  const buttonsContainer = document.createElement('div');
  buttonsContainer.className = 'category-buttons';
  
  questions.forEach((question, idx) => {
    const button = document.createElement('button');
    button.className = 'category-btn';
    button.textContent = question;
    button.onclick = () => {
      inputEl.value = question;
      submitText();
    };
    buttonsContainer.appendChild(button);
  });
  
  messageElement.appendChild(buttonsContainer);
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
  if (!element) {
    console.error('[RENDER] updateBubble called with null element');
    return;
  }
  
  const bubble = element.querySelector('.bubble');
  if (!bubble) {
    console.error('[RENDER] No bubble element found');
    return;
  }
  
  // Ensure text is a string
  const textContent = String(text || '');
  
  // Preserve flowchart container if it exists
  const existingFlowchart = bubble.querySelector('.flowchart-container');
  
  // Render markdown if available and element is a bot message
  if (element.classList.contains('bot') && window.marked && textContent) {
    try {
      bubble.innerHTML = marked.parse(textContent);
      
      // Re-append flowchart if it was present
      if (existingFlowchart) {
        bubble.appendChild(existingFlowchart);
      }
    } catch (err) {
      console.error('[MARKDOWN] Parse error:', err);
      bubble.textContent = textContent;
    }
  } else {
    bubble.textContent = textContent;
  }
  
  bubble.className = 'bubble' + (streaming ? ' streaming' : '');
  chat.scrollTop = chat.scrollHeight;
}

// WebSocket connection
function connectWebsocket() {
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = wsProtocol + "//" + window.location.host + "/ws/" + userId + "/" + sessionId + "?language=" + sessionLanguage;
  
  websocket = new WebSocket(wsUrl);
  
  websocket.onopen = function() {
    console.log("[WEBSOCKET] Connected with language:", sessionLanguage);
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
  // Handle welcome message (only once per conversation)
  if (event.type === 'welcome' && !welcomeReceived) {
    welcomeReceived = true;
    clearEmpty();
    const welcomeRow = appendMessage('bot', event.message);
    if (event.prompts && event.prompts.length > 0) {
      renderPromptButtons(event.prompts, welcomeRow);
    }
    return;
  }
  
  // Handle suggested prompts (follow-up questions)
  if (event.type === 'suggested_prompts') {
    if (event.prompts && event.prompts.length > 0) {
      // Add buttons below the last bot message
      const lastBotRow = Array.from(chat.querySelectorAll('.row.bot')).pop();
      if (lastBotRow) {
        renderPromptButtons(event.prompts, lastBotRow);
      }
    }
    return;
  }
  
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
      // Just remove streaming class without re-rendering to preserve flowcharts
      const bubble = currentBubbleElement.querySelector('.bubble');
      if (bubble) {
        bubble.classList.remove('streaming');
      }
    }
    if (currentOutputTranscriptionElement) {
      // Just remove streaming class without re-rendering to preserve flowcharts
      const bubble = currentOutputTranscriptionElement.querySelector('.bubble');
      if (bubble) {
        bubble.classList.remove('streaming');
      }
    }
    
    // Only stop recording for microphone mode, not voice mode
    if (isRecording && !inVoiceSession) {
      stopRecording();
    }
    
    currentMessageId = null;
    currentBubbleElement = null;
    currentInputTranscriptionElement = null;
    currentOutputTranscriptionElement = null;
    isAgentSpeaking = false;
    // Don't reset lastUsedMode - keep it for the session
    speechBuffer = '';
    
    // Update status based on session state
    if (inVoiceSession) {
      setStatus('audio mode active');
    } else {
      setStatus('ready');
    }
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
    
    // Only stop recording for microphone mode, not voice mode
    if (isRecording && !inVoiceSession) {
      stopRecording();
    }
    
    currentMessageId = null;
    currentBubbleElement = null;
    currentInputTranscriptionElement = null;
    currentOutputTranscriptionElement = null;
    isAgentSpeaking = false;
    // Don't reset lastUsedMode - keep it for the session
    speechBuffer = '';
    
    // Update status based on session state
    if (inVoiceSession) {
      setStatus('audio mode active');
    } else {
      setStatus('ready');
    }
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
    
    // When finished, show as user message and track in history
    if (isFinished) {
      // Only stop recording for microphone mode, not voice mode (continuous conversation)
      if (currentVoiceMode === 'microphone') {
        stopRecording();
      }
      clearEmpty();
      appendMessage('user', text);
      
      // Track user message in local history
      conversationHistory.push({ role: 'user', text: text });
      
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
    if (inVoiceSession) {
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
        renderAssistantResponse(speechBuffer);
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
        renderAssistantResponse(text);
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
        
        // Handle audio playback
        if (mimeType && mimeType.startsWith("audio/pcm") && audioPlayerNode && inVoiceSession) {
          audioPlayerNode.port.postMessage(base64ToArray(data));
        }
        
        // Handle image display
        if (mimeType && mimeType.startsWith("image/")) {
          if (!currentBubbleElement) {
            currentMessageId = Math.random().toString(36).substring(7);
            currentBubbleElement = appendMessage('bot', '', true);
          }
          
          const imageContainer = document.createElement('div');
          imageContainer.className = 'algorithm-image';
          imageContainer.innerHTML = `<img src="data:${mimeType};base64,${data}" alt="Algorithm visualization" />`;
          currentBubbleElement.querySelector('.bubble').appendChild(imageContainer);
        }
      }
      
      // Text data (only if no transcription is handling it)
      if (part.text && !part.thought && !currentOutputTranscriptionElement) {
        if (!currentBubbleElement) {
          currentMessageId = Math.random().toString(36).substring(7);
          currentBubbleElement = appendMessage('bot', part.text, true);
        } else {
          const bubble = currentBubbleElement.querySelector('.bubble');
          const existingText = bubble ? bubble.textContent : '';
          updateBubble(currentBubbleElement, existingText + part.text, true);
        }
        
        // Track complete text messages
        if (event.turnComplete && currentBubbleElement) {
          const bubble = currentBubbleElement.querySelector('.bubble');
          const finalText = bubble ? bubble.textContent : '';
          if (finalText) {
            renderAssistantResponse(finalText);
          }
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

// ========================================
// Bias Report Modal
// ========================================

const flagBiasBtn = document.getElementById('flag-bias-btn');
const biasModal = document.getElementById('bias-modal');
const modalCloseBtn = document.getElementById('modal-close-btn');
const biasTitle = document.getElementById('bias-title');
const biasEmail = document.getElementById('bias-email');
const biasBody = document.getElementById('bias-body');
const biasExplanation = document.getElementById('bias-explanation');
const discardBtn = document.getElementById('discard-btn');
const submitBiasBtn = document.getElementById('submit-bias-btn');
const modalForm = document.getElementById('modal-form');
const modalThankYou = document.getElementById('modal-thank-you');
const modalLoading = document.getElementById('modal-loading');
const thankYouSummary = document.getElementById('thank-you-summary');
const emailResponse = document.getElementById('email-response');

flagBiasBtn.addEventListener('click', openBiasModal);
modalCloseBtn.addEventListener('click', closeBiasModal);
discardBtn.addEventListener('click', closeBiasModal);
submitBiasBtn.addEventListener('click', submitBiasReport);

biasModal.addEventListener('click', (e) => {
  if (e.target === biasModal) {
    closeBiasModal();
  }
});

async function openBiasModal() {
  biasModal.classList.remove('hidden');
  modalForm.classList.add('hidden');
  modalThankYou.classList.add('hidden');
  modalLoading.classList.remove('hidden');
  
  // Reset form fields
  biasTitle.value = '';
  biasEmail.value = '';
  biasBody.value = '';
  biasExplanation.value = '';
  
  try {
    // Generate context using Gemini
    const response = await fetch('/api/generate-bias-context', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_history: conversationHistory.slice(-10).map(msg => ({
          role: msg.role,
          text: msg.text
        }))
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to generate context');
    }
    
    const data = await response.json();
    
    // Populate fields
    biasTitle.value = data.title;
    biasBody.value = data.body;
    
    // Show form
    modalLoading.classList.add('hidden');
    modalForm.classList.remove('hidden');
    
  } catch (error) {
    console.error('Error generating bias context:', error);
    
    // Fallback values
    biasTitle.value = 'Bias Report';
    biasBody.value = 'A conversation about NYC algorithmic tools raised potential bias concerns that warrant review.';
    
    modalLoading.classList.add('hidden');
    modalForm.classList.remove('hidden');
  }
}

function closeBiasModal() {
  biasModal.classList.add('hidden');
  modalForm.classList.remove('hidden');
  modalThankYou.classList.add('hidden');
  modalLoading.classList.add('hidden');
}

async function submitBiasReport() {
  const title = biasTitle.value.trim();
  const email = biasEmail.value.trim();
  const body = biasBody.value.trim();
  const explanation = biasExplanation.value.trim();
  
  // Validate required fields
  if (!explanation) {
    alert(t('explainRequired', currentLanguage));
    return;
  }
  
  // Validate email format if provided
  if (email && !isValidEmail(email)) {
    alert(t('invalidEmail', currentLanguage));
    return;
  }
  
  // Disable submit button
  submitBiasBtn.disabled = true;
  submitBiasBtn.textContent = t('submitting', currentLanguage);
  
  try {
    const response = await fetch('/api/flag-bias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title,
        body: body,
        email: email || null,
        user_explanation: explanation
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to submit bias report');
    }
    
    const data = await response.json();
    
    // Show thank you message
    modalForm.classList.add('hidden');
    thankYouSummary.textContent = data.summary;
    
    if (email) {
      emailResponse.classList.remove('hidden');
    } else {
      emailResponse.classList.add('hidden');
    }
    
    modalThankYou.classList.remove('hidden');
    
    // Close modal after delay
    setTimeout(() => {
      closeBiasModal();
      submitBiasBtn.disabled = false;
      submitBiasBtn.textContent = t('submit', currentLanguage);
    }, 4000);
    
  } catch (error) {
    console.error('Error submitting bias report:', error);
    alert(t('submitError', currentLanguage));
    submitBiasBtn.disabled = false;
    submitBiasBtn.textContent = t('submit', currentLanguage);
  }
}

function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// ========================================
// New Conversation
// ========================================

const newConversationBtn = document.getElementById('new-conversation-btn');
newConversationBtn.addEventListener('click', resetConversation);

function resetConversation() {
  // Close existing websocket if open
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.close();
  }
  
  // End voice session if active
  if (inVoiceSession) {
    endVoiceSession();
  }
  
  // Stop recording if active
  if (isRecording) {
    stopRecording();
  }
  
  // Clear chat UI
  chat.innerHTML = `<div class="empty" id="empty"><p>${t('emptyState', currentLanguage)}</p></div>`;
  empty = document.getElementById('empty');
  
  // Reset all conversation state
  conversationHistory = [];
  lastOptions = [];
  currentTopic = null;
  currentSubtopic = null;
  clarificationDepth = 0;
  welcomeReceived = false;
  
  // Reset message tracking state
  currentMessageId = null;
  currentBubbleElement = null;
  currentInputTranscriptionElement = null;
  currentOutputTranscriptionElement = null;
  isAgentSpeaking = false;
  typingIndicator = null;
  speechBuffer = '';
  if (speechRevealInterval) {
    clearInterval(speechRevealInterval);
    speechRevealInterval = null;
  }
  
  // Generate new session ID
  sessionId = "session-" + Math.random().toString(36).substring(7);
  
  // Lock in the current language for this new session
  sessionLanguage = currentLanguage;
  
  // Reconnect with new session
  connectWebsocket();
  
  console.log('[CONVERSATION] Reset to new conversation with sessionId:', sessionId, 'language:', sessionLanguage);
}

// ========================================
// Initialize
// ========================================
// Set initial UI state for language
currentFlag.textContent = getFlag(currentLanguage);
document.querySelectorAll('.language-option').forEach(option => {
  if (option.dataset.lang === currentLanguage) {
    option.classList.add('active');
  } else {
    option.classList.remove('active');
  }
});

applyTranslations();
connectWebsocket();
inputEl.focus();
