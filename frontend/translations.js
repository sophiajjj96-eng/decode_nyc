/**
 * Translation dictionary for multi-language support
 * Supports: English (en), Spanish (es), Simplified Chinese (zh-CN)
 */

export const translations = {
  en: {
    // Header
    appTitle: "Decode NYC",
    newConversation: "Start new conversation",
    flagBias: "Flag for bias",
    
    // Input and buttons
    inputPlaceholder: "e.g. Does the NYPD use AI to make decisions about me?",
    sendMessage: "Send message",
    speechToText: "Speech to text",
    voiceConversation: "Voice conversation",
    stopRecording: "Click to stop",
    stopMicFirst: "Stop microphone first",
    stopRecordingFirst: "Stop recording first",
    disableAudioMode: "Click to disable audio mode",
    enableAudioMode: "Click to enable audio mode",
    
    // Empty state
    emptyState: "Find out how NYC's algorithms affect you",
    
    // Status labels
    statusReady: "ready",
    statusConnected: "connected",
    statusAudioInit: "audio initialized",
    statusAudioActive: "audio mode active",
    statusListening: "listening…",
    statusAgentSpeaking: "agent speaking…",
    statusReconnecting: "reconnecting…",
    statusError: "error",
    
    // Bias modal
    modalTitle: "Flag for Bias",
    issueSummary: "Issue Summary",
    contactEmail: "Contact Email",
    optional: "(optional)",
    conversationContext: "Conversation Context",
    yourExplanation: "Your Explanation",
    explanationPlaceholder: "Describe the bias issue you observed...",
    discard: "Discard",
    submit: "Submit",
    submitting: "Submitting...",
    thankYou: "Thank You",
    apology: "We apologize for any inconvenience. This feedback is taken very seriously and valued.",
    emailResponse: "We'll respond to your email soon.",
    generatingContext: "Generating report context...",
    
    // Validation messages
    explainRequired: "Please provide an explanation of the bias issue.",
    invalidEmail: "Please enter a valid email address or leave it empty.",
    submitError: "Failed to submit bias report. Please try again.",
    audioPermissionError: "Could not start audio. Please check microphone permissions.",
  },
  
  es: {
    // Header
    appTitle: "Decode NYC",
    newConversation: "Iniciar nueva conversación",
    flagBias: "Reportar sesgo",
    
    // Input and buttons
    inputPlaceholder: "ej. ¿La policía de Nueva York usa IA para tomar decisiones sobre mí?",
    sendMessage: "Enviar mensaje",
    speechToText: "Voz a texto",
    voiceConversation: "Conversación por voz",
    stopRecording: "Haz clic para detener",
    stopMicFirst: "Detén el micrófono primero",
    stopRecordingFirst: "Detén la grabación primero",
    disableAudioMode: "Haz clic para desactivar modo de audio",
    enableAudioMode: "Haz clic para activar modo de audio",
    
    // Empty state
    emptyState: "Descubre cómo los algoritmos de NYC te afectan",
    
    // Status labels
    statusReady: "listo",
    statusConnected: "conectado",
    statusAudioInit: "audio inicializado",
    statusAudioActive: "modo de audio activo",
    statusListening: "escuchando…",
    statusAgentSpeaking: "agente hablando…",
    statusReconnecting: "reconectando…",
    statusError: "error",
    
    // Bias modal
    modalTitle: "Reportar Sesgo",
    issueSummary: "Resumen del Problema",
    contactEmail: "Correo Electrónico",
    optional: "(opcional)",
    conversationContext: "Contexto de la Conversación",
    yourExplanation: "Tu Explicación",
    explanationPlaceholder: "Describe el problema de sesgo que observaste...",
    discard: "Descartar",
    submit: "Enviar",
    submitting: "Enviando...",
    thankYou: "Gracias",
    apology: "Pedimos disculpas por cualquier inconveniente. Valoramos mucho tus comentarios.",
    emailResponse: "Te responderemos a tu correo pronto.",
    generatingContext: "Generando contexto del reporte...",
    
    // Validation messages
    explainRequired: "Por favor, proporciona una explicación del problema de sesgo.",
    invalidEmail: "Por favor, ingresa un correo electrónico válido o déjalo vacío.",
    submitError: "No se pudo enviar el reporte de sesgo. Por favor, intenta de nuevo.",
    audioPermissionError: "No se pudo iniciar el audio. Por favor, verifica los permisos del micrófono.",
  },
  
  'zh-CN': {
    // Header
    appTitle: "Decode NYC",
    newConversation: "开始新对话",
    flagBias: "报告偏见",
    
    // Input and buttons
    inputPlaceholder: "例如：纽约警察局是否使用人工智能对我做出决定？",
    sendMessage: "发送消息",
    speechToText: "语音转文字",
    voiceConversation: "语音对话",
    stopRecording: "点击停止",
    stopMicFirst: "请先停止麦克风",
    stopRecordingFirst: "请先停止录音",
    disableAudioMode: "点击关闭音频模式",
    enableAudioMode: "点击启用音频模式",
    
    // Empty state
    emptyState: "了解纽约市的算法如何影响您",
    
    // Status labels
    statusReady: "就绪",
    statusConnected: "已连接",
    statusAudioInit: "音频已初始化",
    statusAudioActive: "音频模式已激活",
    statusListening: "正在听…",
    statusAgentSpeaking: "助手正在说话…",
    statusReconnecting: "重新连接中…",
    statusError: "错误",
    
    // Bias modal
    modalTitle: "报告偏见",
    issueSummary: "问题摘要",
    contactEmail: "联系邮箱",
    optional: "（可选）",
    conversationContext: "对话背景",
    yourExplanation: "您的说明",
    explanationPlaceholder: "描述您观察到的偏见问题...",
    discard: "放弃",
    submit: "提交",
    submitting: "提交中...",
    thankYou: "谢谢",
    apology: "对于任何不便，我们深表歉意。我们非常重视您的反馈。",
    emailResponse: "我们将很快回复您的邮件。",
    generatingContext: "正在生成报告背景...",
    
    // Validation messages
    explainRequired: "请提供对偏见问题的说明。",
    invalidEmail: "请输入有效的电子邮件地址或留空。",
    submitError: "提交偏见报告失败。请重试。",
    audioPermissionError: "无法启动音频。请检查麦克风权限。",
  }
};

/**
 * Get translated string for a key
 * @param {string} key - Translation key
 * @param {string} lang - Language code (en, es, zh-CN)
 * @returns {string} Translated string or key if not found
 */
export function t(key, lang = 'en') {
  return translations[lang]?.[key] || translations.en[key] || key;
}

/**
 * Get language display name
 * @param {string} lang - Language code
 * @returns {string} Display name
 */
export function getLanguageName(lang) {
  const names = {
    en: 'English',
    es: 'Español',
    'zh-CN': '简体中文'
  };
  return names[lang] || lang;
}

/**
 * Get flag emoji for language
 * @param {string} lang - Language code
 * @returns {string} Flag emoji
 */
export function getFlag(lang) {
  const flags = {
    en: '🇺🇸',
    es: '🇪🇸',
    'zh-CN': '🇨🇳'
  };
  return flags[lang] || '🌐';
}

/**
 * Get all supported languages
 * @returns {Array} Array of {code, name, flag}
 */
export function getSupportedLanguages() {
  return [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'zh-CN', name: '简体中文', flag: '🇨🇳' }
  ];
}
