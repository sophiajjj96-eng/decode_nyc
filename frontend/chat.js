const chat = document.getElementById('chat');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send');
const micBtn = document.getElementById('mic-btn');
const micLabel = document.getElementById('mic-label');
const voiceBars = document.getElementById('voice-bars');
const statusLabel = document.getElementById('status-label');
let empty = document.getElementById('empty');

let currentMode = 'text';
let voiceState = 'idle';
let recognition = null;
let liveRow = null;

let conversationHistory = [];
let lastOptions = [];
let currentTopic = null;
let currentSubtopic = null;
let clarificationDepth = 0;

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
micBtn.addEventListener('click', handleMicClick);

async function submitText(prefilledText = null) {
  const text = (prefilledText ?? inputEl.value).trim();
  if (!text) return;

  clearEmpty();
  appendMessage('user', text);

  conversationHistory.push({ role: 'user', text });

  inputEl.value = '';
  inputEl.style.height = 'auto';
  setStatus('thinking…');

  const typingRow = showTyping();

  try {
    const reply = await getReply(text);
    typingRow.remove();
    renderAssistantResponse(reply);
    setStatus('ready');
  } catch (err) {
    typingRow.remove();
    appendMessage('bot', `Something went wrong: ${err.message}`);
    setStatus('error');
    console.error(err);
  }
}

function handleMicClick() {
  if (voiceState === 'idle') startSession();
  else stopSession();
}

function setVoiceState(state) {
  voiceState = state;

  micBtn.classList.remove('idle', 'listening', 'speaking');
  micBtn.classList.add(state);

  if (state === 'idle') {
    micLabel.textContent = 'Start conversation';
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

function startSession() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    clearEmpty();
    appendMessage('bot', 'Voice requires Chrome or another browser with SpeechRecognition support and HTTPS. Please use text mode or switch browsers.');
    return;
  }

  setVoiceState('listening');
  liveRow = null;
  clearEmpty();

  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = true;
  recognition.continuous = true;

  recognition.onresult = (event) => {
    let interim = '';
    let final = '';

    for (const result of event.results) {
      if (result.isFinal) final += result[0].transcript;
      else interim += result[0].transcript;
    }

    const display = (final + interim).trim();
    if (!display) return;

    if (!liveRow) {
      liveRow = appendMessage('user', display, true);
    } else {
      liveRow.querySelector('.bubble').textContent = display;
      chat.scrollTop = chat.scrollHeight;
    }
  };

  recognition.onerror = (e) => {
    if (e.error === 'not-allowed') {
      appendMessage('bot', 'Microphone access denied. Allow mic permissions and try again.');
    } else if (e.error === 'network') {
      appendMessage('bot', 'Voice recognition requires an internet connection.');
    }
    stopSession();
  };

  recognition.onend = () => {
    if (voiceState === 'listening') finishSpeaking();
  };

  try {
    recognition.start();
  } catch (err) {
    appendMessage('bot', 'Could not start voice recognition. Make sure you are on HTTPS.');
    setVoiceState('idle');
  }
}

function stopSession() {
  if (recognition) {
    recognition.onend = null;
    recognition.stop();
    recognition = null;
  }
  finishSpeaking();
}

async function finishSpeaking() {
  const text = liveRow?.querySelector('.bubble')?.textContent?.trim();
  if (liveRow) liveRow.querySelector('.bubble').classList.remove('streaming');
  liveRow = null;

  if (!text) {
    setVoiceState('idle');
    return;
  }

  conversationHistory.push({ role: 'user', text });

  setVoiceState('speaking');
  const typingRow = showTyping();

  try {
    const reply = await getReply(text);
    typingRow.remove();
    renderAssistantResponse(reply);
    setVoiceState('idle');
  } catch (err) {
    typingRow.remove();
    appendMessage('bot', `Something went wrong: ${err.message}`);
    setVoiceState('idle');
    console.error(err);
  }
}

function renderAssistantResponse(data) {
  const answerText = data.answer || 'I could not generate a reply.';
  appendMessage('bot', answerText);
  conversationHistory.push({ role: 'assistant', text: answerText });

  currentTopic = data.current_topic ?? currentTopic;
  currentSubtopic = data.current_subtopic ?? currentSubtopic;
  clarificationDepth = Number.isInteger(data.clarification_depth)
    ? data.clarification_depth
    : clarificationDepth;

  if (Array.isArray(data.options) && data.options.length > 0) {
    lastOptions = data.options;
  } else {
    lastOptions = [];
  }
}

function clearEmpty() {
  if (empty) {
    empty.remove();
    empty = null;
  }
}

function appendMessage(role, text, streaming = false) {
  const row = document.createElement('div');
  row.className = `row ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? 'You' : 'AI';

  const bubble = document.createElement('div');
  bubble.className = 'bubble' + (streaming ? ' streaming' : '');

  if (role === 'bot' && window.marked) {
    bubble.innerHTML = marked.parse(text);
  } else {
    bubble.textContent = text;
  }

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

async function getReply(message) {
  const res = await fetch('http://127.0.0.1:8000/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question: message,
      history: conversationHistory,
      last_options: lastOptions,
      current_topic: currentTopic,
      current_subtopic: currentSubtopic,
      clarification_depth: clarificationDepth,
    }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || 'Backend error');
  }

  return await res.json();
}

setMode('text');
