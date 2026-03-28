/**
 * Algorithm flowchart visualization using Mermaid.js
 */

// Flowchart definitions for each algorithm
const FLOWCHART_DEFINITIONS = {
  homebase_raq: `
flowchart TD
    Start[Homebase Application] --> Questions[Answer Questions]
    Questions --> PriorDHS{Prior DHS Contact?}
    PriorDHS -->|Yes| LowerScore[Score Reduced]
    PriorDHS -->|No| CheckLength[Check Housing Length]
    LowerScore --> CheckLength
    CheckLength --> Income{Income Level}
    Income -->|Low| HighRisk[High Risk Score]
    Income -->|Medium/High| ModerateRisk[Moderate Risk]
    HighRisk --> Eligible[Likely Eligible]
    ModerateRisk --> MaybeEligible[May Qualify]
    MaybeEligible --> Decision[Caseworker Decision]
    Eligible --> Decision
    Decision --> Services[Prevention Services]
`,

  myschools: `
flowchart TD
    Start[Student Applies] --> Rank[Submit School Rankings]
    Rank --> Address{Home Address}
    Address --> SchoolRank[Schools Rank Students]
    SchoolRank --> Match[Gale-Shapley Algorithm]
    Match --> Probability[Calculate Acceptance Probability]
    Probability --> Result{Match Found?}
    Result -->|Yes| Assigned[Assigned to School]
    Result -->|No| Waitlist[Added to Waitlist]
    Assigned --> Appeal[Can Appeal]
    Waitlist --> Appeal
`,

  acs_repeat_maltreatment: `
flowchart TD
    Start[ACS Investigation Opens] --> History{Prior ACS Contact?}
    History -->|Yes| HighScore[Higher Risk Score]
    History -->|No| BaseScore[Base Risk Score]
    HighScore --> Model[Predictive Model]
    BaseScore --> Model
    Model --> Ranking[Case Ranked by Risk]
    Ranking --> Priority{High Priority?}
    Priority -->|Yes| ImmediateReview[Immediate Caseworker Review]
    Priority -->|No| StandardReview[Standard Processing]
    ImmediateReview --> Investigation[Investigation Proceeds]
    StandardReview --> Investigation
`,

  shotspotter: `
flowchart TD
    Start[Audio Signal Detected] --> Sensors[Microphone Array]
    Sensors --> Algorithm[Proprietary Algorithm]
    Algorithm --> Analysis{Gunshot Detected?}
    Analysis -->|Yes| Location[Determine Location]
    Analysis -->|No| Discard[No Action]
    Location --> Dispatch[Police Dispatch]
    Dispatch --> Response[Officers Respond]
    Response --> FalsePositive{Was It a Gunshot?}
    FalsePositive -->|No| FalseAlert[False Positive]
    FalsePositive -->|Yes| ValidAlert[Valid Alert]
`
};

/**
 * Render a flowchart for the given algorithm
 * @param {string} algorithmId - Algorithm ID (homebase_raq, myschools, etc.)
 * @param {HTMLElement} container - Container element to render into
 */
export async function renderFlowchart(algorithmId, container) {
  if (!container) {
    console.error('[FLOWCHART] No container provided');
    return;
  }
  
  const definition = FLOWCHART_DEFINITIONS[algorithmId];
  
  if (!definition) {
    container.innerHTML = '<p class="no-flowchart">Flowchart not available for this algorithm.</p>';
    return;
  }
  
  try {
    // Load mermaid.js if not already loaded
    if (!window.mermaid) {
      const script = document.createElement('script');
      // Use UMD build that exposes window.mermaid
      script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js';
      script.type = 'text/javascript';
      document.head.appendChild(script);
      
      // Wait for mermaid to load
      await new Promise((resolve, reject) => {
        script.onload = () => {
          if (window.mermaid) {
            resolve();
          } else {
            reject(new Error('Mermaid loaded but not available on window'));
          }
        };
        script.onerror = () => reject(new Error('Failed to load mermaid.js'));
        setTimeout(() => reject(new Error('Mermaid load timeout')), 10000);
      });
      
      // Initialize mermaid
      window.mermaid.initialize({ 
        startOnLoad: false,
        theme: 'neutral',
        flowchart: {
          useMaxWidth: true,
          htmlLabels: true,
          curve: 'basis'
        }
      });
    }
    
    // Create a unique ID for this chart
    const chartId = `flowchart-${algorithmId}-${Date.now()}`;
    container.innerHTML = `<div class="mermaid" id="${chartId}">${definition}</div>`;
    
    // Render the chart
    const chartElement = container.querySelector(`#${chartId}`);
    if (chartElement) {
      await window.mermaid.run({
        nodes: [chartElement]
      });
    }
  } catch (error) {
    console.error('[FLOWCHART] Rendering error:', error);
    container.innerHTML = '<p class="flowchart-error">Unable to render flowchart.</p>';
  }
}

/**
 * Detect if a message contains an algorithm explanation and inject flowchart
 * @param {HTMLElement} messageElement - The message bubble element
 * @param {string} messageText - The message text content
 */
export async function injectFlowchartIfNeeded(messageElement, messageText) {
  if (!messageElement || !messageText) {
    return;
  }
  
  const lowerText = messageText.toLowerCase();
  
  // Detect algorithm keywords
  let algorithmId = null;
  
  if (lowerText.includes('homebase') || (lowerText.includes('risk assessment') && lowerText.includes('questionnaire'))) {
    algorithmId = 'homebase_raq';
  } else if (lowerText.includes('myschools') || (lowerText.includes('gale-shapley') && lowerText.includes('school'))) {
    algorithmId = 'myschools';
  } else if (lowerText.includes('acs') && (lowerText.includes('repeat') || lowerText.includes('maltreatment'))) {
    algorithmId = 'acs_repeat_maltreatment';
  } else if (lowerText.includes('shotspotter')) {
    algorithmId = 'shotspotter';
  }
  
  if (!algorithmId) {
    return;
  }
  
  // Check if flowchart already exists
  if (messageElement.querySelector('.flowchart-container')) {
    return;
  }
  
  // Find bubble element
  const bubble = messageElement.querySelector('.bubble');
  if (!bubble) {
    console.error('[FLOWCHART] No bubble element found in message');
    return;
  }
  
  // Create flowchart container
  const flowchartContainer = document.createElement('div');
  flowchartContainer.className = 'flowchart-container';
  flowchartContainer.innerHTML = '<div class="flowchart-title">How This Algorithm Works</div><div class="flowchart-content"></div>';
  
  const contentDiv = flowchartContainer.querySelector('.flowchart-content');
  bubble.appendChild(flowchartContainer);
  
  // Render flowchart
  await renderFlowchart(algorithmId, contentDiv);
}
