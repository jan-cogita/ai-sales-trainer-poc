/**
 * AI Sales Trainer - Complete Application
 * Tab-based interface with multiple AI assistants
 */

// ========================================
// Tab Navigation
// ========================================
class TabManager {
    constructor() {
        this.tabButtons = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');
        this.bindEvents();
    }

    bindEvents() {
        this.tabButtons.forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });
    }

    switchTab(tabId) {
        // Update buttons
        this.tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        // Update content
        this.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `${tabId}Tab`);
        });
    }
}

// ========================================
// Practice Tab - Chat Application (Existing)
// ========================================
class ChatApp {
    constructor() {
        this.conversationId = null;
        this.currentScenario = null;
        this.scenarios = [];
        this.isLoading = false;

        // DOM elements - Screens
        this.scenarioScreen = document.getElementById('scenarioScreen');
        this.chatScreen = document.getElementById('chatScreen');
        this.evaluationScreen = document.getElementById('evaluationScreen');

        // DOM elements - Scenario selection
        this.scenarioList = document.getElementById('scenarioList');

        // DOM elements - Chat
        this.scenarioTitle = document.getElementById('scenarioTitle');
        this.personaInfo = document.getElementById('personaInfo');
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.endSessionBtn = document.getElementById('endSessionBtn');

        // DOM elements - Evaluation
        this.overallScore = document.getElementById('overallScore');
        this.evaluationSummary = document.getElementById('evaluationSummary');
        this.dimensionScores = document.getElementById('dimensionScores');
        this.strengthsList = document.getElementById('strengthsList');
        this.improvementsList = document.getElementById('improvementsList');
        this.practiceAgainBtn = document.getElementById('practiceAgainBtn');

        this.bindEvents();
        this.loadScenarios();
    }

    bindEvents() {
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.endSessionBtn.addEventListener('click', () => this.endConversation());
        this.practiceAgainBtn.addEventListener('click', () => this.showScenarioScreen());
    }

    showScreen(screen) {
        this.scenarioScreen.classList.add('hidden');
        this.chatScreen.classList.add('hidden');
        this.evaluationScreen.classList.add('hidden');
        screen.classList.remove('hidden');
    }

    showScenarioScreen() {
        this.conversationId = null;
        this.currentScenario = null;
        this.showScreen(this.scenarioScreen);
        this.loadScenarios();
    }

    showChatScreen() {
        this.showScreen(this.chatScreen);
        this.chatMessages.innerHTML = '';
        this.messageInput.value = '';
        this.messageInput.focus();
    }

    showEvaluationScreen() {
        this.showScreen(this.evaluationScreen);
    }

    async loadScenarios() {
        try {
            const resp = await fetch('/scenarios');
            if (!resp.ok) throw new Error('Failed to load scenarios');
            const data = await resp.json();
            this.scenarios = data.scenarios;
            this.renderScenarios(this.scenarios);
        } catch (error) {
            console.error('Error loading scenarios:', error);
            this.scenarioList.innerHTML = '<div class="error">Failed to load scenarios. Please refresh the page.</div>';
        }
    }

    async startConversation(scenarioId) {
        if (this.isLoading) return;
        this.setLoading(true);

        this.currentScenario = this.scenarios.find(s => s.id === scenarioId);
        if (!this.currentScenario) {
            alert('Scenario not found');
            this.setLoading(false);
            return;
        }

        try {
            const resp = await fetch('/chat/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenario_id: scenarioId })
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || 'Failed to start conversation');
            }

            const data = await resp.json();
            this.conversationId = data.conversation.id;

            this.scenarioTitle.textContent = this.currentScenario.title;
            this.personaInfo.textContent = `${this.currentScenario.persona.name}, ${this.currentScenario.persona.role} at ${this.currentScenario.persona.company}`;

            this.showChatScreen();
            this.addMessage('assistant', data.opening_message.content);
            this.enableInput();

        } catch (error) {
            console.error('Error starting conversation:', error);
            alert('Failed to start conversation: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }

    async sendMessage() {
        const content = this.messageInput.value.trim();
        if (!content || this.isLoading || !this.conversationId) return;

        this.disableInput();
        this.addMessage('user', content);
        this.messageInput.value = '';
        this.showTypingIndicator();

        try {
            const resp = await fetch('/chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversation_id: this.conversationId,
                    content: content
                })
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || 'Failed to send message');
            }

            const data = await resp.json();
            this.hideTypingIndicator();
            this.addMessage('assistant', data.message.content);
            this.enableInput();
            this.messageInput.focus();

        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.addMessage('system', 'Error: ' + error.message);
            this.enableInput();
        }
    }

    async endConversation() {
        if (!this.conversationId || this.isLoading) return;

        if (!confirm('End this practice session and see your evaluation?')) return;

        this.setLoading(true);
        this.disableInput();
        this.showTypingIndicator('Generating evaluation...');

        try {
            const resp = await fetch(`/chat/${this.conversationId}/end`, {
                method: 'POST'
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || 'Failed to end conversation');
            }

            const data = await resp.json();
            this.hideTypingIndicator();
            this.displayEvaluation(data.evaluation);
            this.showEvaluationScreen();

        } catch (error) {
            console.error('Error ending conversation:', error);
            this.hideTypingIndicator();
            alert('Failed to get evaluation: ' + error.message);
            this.enableInput();
        } finally {
            this.setLoading(false);
        }
    }

    renderScenarios(scenarios) {
        this.scenarioList.innerHTML = scenarios.map(scenario => `
            <div class="scenario-card" data-id="${scenario.id}">
                <div class="scenario-header">
                    <h3>${this.escapeHtml(scenario.title)}</h3>
                    <span class="difficulty-badge difficulty-${scenario.difficulty}">${scenario.difficulty}</span>
                </div>
                <p class="scenario-description">${this.escapeHtml(scenario.description)}</p>
                <div class="scenario-meta">
                    <span class="persona">${this.escapeHtml(scenario.persona.name)}, ${this.escapeHtml(scenario.persona.role)}</span>
                    <span class="methodology">${this.escapeHtml(scenario.methodology.toUpperCase())}</span>
                </div>
                <button class="btn btn-primary start-btn">Start Practice</button>
            </div>
        `).join('');

        this.scenarioList.querySelectorAll('.start-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const card = e.target.closest('.scenario-card');
                const scenarioId = card.dataset.id;
                this.startConversation(scenarioId);
            });
        });
    }

    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const roleLabel = role === 'user' ? 'You' :
                         role === 'assistant' ? (this.currentScenario?.persona?.name || 'Customer') :
                         'System';

        messageDiv.innerHTML = `
            <div class="message-role">${this.escapeHtml(roleLabel)}</div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator(text = 'Typing...') {
        const indicator = document.createElement('div');
        indicator.className = 'message assistant typing-indicator';
        indicator.id = 'typingIndicator';
        indicator.innerHTML = `
            <div class="message-role">${this.escapeHtml(this.currentScenario?.persona?.name || 'Customer')}</div>
            <div class="message-content"><span class="dots">${this.escapeHtml(text)}</span></div>
        `;
        this.chatMessages.appendChild(indicator);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) indicator.remove();
    }

    displayEvaluation(evaluation) {
        this.overallScore.textContent = evaluation.overall_score.toFixed(1);
        this.overallScore.className = 'score-number ' + this.getScoreClass(evaluation.overall_score);

        this.evaluationSummary.textContent = evaluation.summary;

        this.dimensionScores.innerHTML = evaluation.dimensions.map(dim => `
            <div class="dimension-card">
                <div class="dimension-header">
                    <span class="dimension-name">${this.escapeHtml(dim.dimension)}</span>
                    <span class="dimension-score ${this.getScoreClass(dim.score)}">${dim.score}/${dim.max_score}</span>
                </div>
                <div class="dimension-bar">
                    <div class="dimension-fill ${this.getScoreClass(dim.score)}" style="width: ${(dim.score / dim.max_score) * 100}%"></div>
                </div>
                <p class="dimension-feedback">${this.escapeHtml(dim.feedback)}</p>
            </div>
        `).join('');

        if (evaluation.strengths && evaluation.strengths.length > 0) {
            this.strengthsList.innerHTML = evaluation.strengths.map(s =>
                `<li>${this.escapeHtml(s)}</li>`
            ).join('');
            this.strengthsList.parentElement.classList.remove('hidden');
        } else {
            this.strengthsList.parentElement.classList.add('hidden');
        }

        if (evaluation.improvements && evaluation.improvements.length > 0) {
            this.improvementsList.innerHTML = evaluation.improvements.map(i =>
                `<li>${this.escapeHtml(i)}</li>`
            ).join('');
            this.improvementsList.parentElement.classList.remove('hidden');
        } else {
            this.improvementsList.parentElement.classList.add('hidden');
        }
    }

    getScoreClass(score) {
        if (score >= 8) return 'score-excellent';
        if (score >= 6) return 'score-good';
        if (score >= 4) return 'score-developing';
        return 'score-needs-work';
    }

    setLoading(loading) {
        this.isLoading = loading;
    }

    enableInput() {
        this.messageInput.disabled = false;
        this.sendBtn.disabled = false;
    }

    disableInput() {
        this.messageInput.disabled = true;
        this.sendBtn.disabled = true;
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ========================================
// Questions Tab - SPIN Question Creator
// ========================================
class QuestionsApp {
    constructor() {
        this.questionType = document.getElementById('questionType');
        this.questionText = document.getElementById('questionText');
        this.analyzeBtn = document.getElementById('analyzeQuestionBtn');
        this.resultsPanel = document.getElementById('questionResults');

        // Result elements
        this.typeAccuracy = document.getElementById('typeAccuracy');
        this.qualityScore = document.getElementById('qualityScore');
        this.isOpenEnded = document.getElementById('isOpenEnded');
        this.strengthsList = document.getElementById('questionStrengths');
        this.improvementsList = document.getElementById('questionImprovements');
        this.improvedQuestion = document.getElementById('improvedQuestion');

        this.bindEvents();
    }

    bindEvents() {
        this.analyzeBtn.addEventListener('click', () => this.analyzeQuestion());
        this.questionText.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault();
                this.analyzeQuestion();
            }
        });
    }

    async analyzeQuestion() {
        const question = this.questionText.value.trim();
        const intendedType = this.questionType.value;

        if (!question) {
            alert('Please enter a question to analyze.');
            return;
        }

        this.setLoading(true);

        try {
            const resp = await fetch('/questions/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    question_type: intendedType
                })
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || 'Failed to analyze question');
            }

            const data = await resp.json();
            this.displayResults(data);

        } catch (error) {
            console.error('Error analyzing question:', error);
            alert('Failed to analyze question: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }

    displayResults(data) {
        // Type accuracy
        const typeMatch = data.actual_type === this.questionType.value;
        this.typeAccuracy.textContent = typeMatch ? 'Correct' : `Actually: ${data.actual_type}`;
        this.typeAccuracy.className = `result-value ${typeMatch ? 'positive' : 'negative'}`;

        // Quality score
        this.qualityScore.textContent = `${data.score}/10`;
        this.qualityScore.className = `result-value ${data.score >= 7 ? 'positive' : data.score >= 5 ? '' : 'negative'}`;

        // Open-ended check
        this.isOpenEnded.textContent = data.is_open_ended ? 'Yes' : 'No';
        this.isOpenEnded.className = `result-value ${data.is_open_ended ? 'positive' : 'negative'}`;

        // Strengths
        if (data.strengths && data.strengths.length > 0) {
            this.strengthsList.innerHTML = data.strengths.map(s => `<li>${this.escapeHtml(s)}</li>`).join('');
            this.strengthsList.parentElement.style.display = 'block';
        } else {
            this.strengthsList.parentElement.style.display = 'none';
        }

        // Improvements
        if (data.improvements && data.improvements.length > 0) {
            this.improvementsList.innerHTML = data.improvements.map(i => `<li>${this.escapeHtml(i)}</li>`).join('');
            this.improvementsList.parentElement.style.display = 'block';
        } else {
            this.improvementsList.parentElement.style.display = 'none';
        }

        // Improved version
        if (data.improved_version) {
            this.improvedQuestion.textContent = data.improved_version;
            this.improvedQuestion.parentElement.style.display = 'block';
        } else {
            this.improvedQuestion.parentElement.style.display = 'none';
        }

        this.resultsPanel.classList.remove('hidden');
    }

    setLoading(loading) {
        this.analyzeBtn.disabled = loading;
        this.analyzeBtn.textContent = loading ? 'Analyzing...' : 'Analyze Question';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ========================================
// Qualify Tab - MEDDPICC Opportunity Qualifier
// ========================================
class QualifyApp {
    constructor() {
        this.opportunityName = document.getElementById('opportunityName');
        this.opportunityContext = document.getElementById('opportunityContext');
        this.analyzeBtn = document.getElementById('analyzeQualificationBtn');
        this.resultsPanel = document.getElementById('qualifyResults');

        // Result elements
        this.qualScore = document.getElementById('qualScore');
        this.qualStatus = document.getElementById('qualStatus');
        this.priorityActions = document.getElementById('priorityActions');

        // MEDDPICC elements mapping
        this.elements = {
            metrics: { status: 'metricsStatus', bar: 'metricsBar', feedback: 'metricsFeedback' },
            economic_buyer: { status: 'econBuyerStatus', bar: 'econBuyerBar', feedback: 'econBuyerFeedback' },
            decision_criteria: { status: 'decisionCriteriaStatus', bar: 'decisionCriteriaBar', feedback: 'decisionCriteriaFeedback' },
            decision_process: { status: 'decisionProcessStatus', bar: 'decisionProcessBar', feedback: 'decisionProcessFeedback' },
            paper_process: { status: 'paperProcessStatus', bar: 'paperProcessBar', feedback: 'paperProcessFeedback' },
            identify_pain: { status: 'identifyPainStatus', bar: 'identifyPainBar', feedback: 'identifyPainFeedback' },
            champion: { status: 'championStatus', bar: 'championBar', feedback: 'championFeedback' },
            competition: { status: 'competitionStatus', bar: 'competitionBar', feedback: 'competitionFeedback' }
        };

        this.bindEvents();
    }

    bindEvents() {
        this.analyzeBtn.addEventListener('click', () => this.analyzeQualification());
    }

    async analyzeQualification() {
        const name = this.opportunityName.value.trim();
        const context = this.opportunityContext.value.trim();

        if (!context) {
            alert('Please describe what you know about this deal.');
            return;
        }

        this.setLoading(true);

        try {
            const resp = await fetch('/qualification/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    context: context
                })
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || 'Failed to analyze qualification');
            }

            const data = await resp.json();
            this.displayResults(data);

        } catch (error) {
            console.error('Error analyzing qualification:', error);
            alert('Failed to analyze qualification: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }

    displayResults(data) {
        // Overall score
        this.qualScore.textContent = data.overall_score;

        // Status badge
        let statusClass, statusText;
        if (data.overall_score >= 70) {
            statusClass = 'strong';
            statusText = 'WELL QUALIFIED';
        } else if (data.overall_score >= 40) {
            statusClass = 'medium';
            statusText = 'NEEDS WORK';
        } else {
            statusClass = 'weak';
            statusText = 'AT RISK';
        }
        this.qualStatus.className = `qual-status ${statusClass}`;
        this.qualStatus.textContent = statusText;

        // MEDDPICC dimensions
        if (data.dimensions) {
            for (const [key, config] of Object.entries(this.elements)) {
                const dimension = data.dimensions[key];
                if (dimension) {
                    const statusEl = document.getElementById(config.status);
                    const barEl = document.getElementById(config.bar);
                    const feedbackEl = document.getElementById(config.feedback);

                    // Map status to strength class and percentage
                    let strengthClass, barWidth;
                    const status = dimension.status?.toLowerCase() || 'missing';
                    if (status === 'strong') {
                        strengthClass = 'strong';
                        barWidth = 100;
                    } else if (status === 'weak') {
                        strengthClass = 'weak';
                        barWidth = 50;
                    } else {
                        strengthClass = 'missing';
                        barWidth = 10;
                    }

                    // Update status badge
                    statusEl.className = `meddpicc-status ${strengthClass}`;
                    statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);

                    // Update bar
                    barEl.className = `meddpicc-fill ${strengthClass}`;
                    barEl.style.width = `${barWidth}%`;

                    // Update feedback - use evidence if strong, gap if weak/missing
                    const feedback = dimension.evidence || dimension.gap || '';
                    feedbackEl.textContent = feedback;
                }
            }
        }

        // Priority actions
        if (data.priority_actions && data.priority_actions.length > 0) {
            this.priorityActions.innerHTML = data.priority_actions.map(a =>
                `<li>${this.escapeHtml(a)}</li>`
            ).join('');
        } else {
            this.priorityActions.innerHTML = '<li>No immediate actions required</li>';
        }

        this.resultsPanel.classList.remove('hidden');
    }

    setLoading(loading) {
        this.analyzeBtn.disabled = loading;
        this.analyzeBtn.textContent = loading ? 'Analyzing...' : 'Analyze Qualification';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ========================================
// Value Prop Tab - Value Proposition Workshop
// ========================================
class ValuePropApp {
    constructor() {
        this.targetCustomer = document.getElementById('targetCustomer');
        this.valueProposition = document.getElementById('valueProposition');
        this.analyzeBtn = document.getElementById('analyzeValuePropBtn');
        this.resultsPanel = document.getElementById('valuepropResults');

        // Result elements
        this.vpOverallScore = document.getElementById('vpOverallScore');
        this.whyStatus = document.getElementById('whyStatus');
        this.whyBar = document.getElementById('whyBar');
        this.whyFeedback = document.getElementById('whyFeedback');
        this.howStatus = document.getElementById('howStatus');
        this.howBar = document.getElementById('howBar');
        this.howFeedback = document.getElementById('howFeedback');
        this.whatStatus = document.getElementById('whatStatus');
        this.whatBar = document.getElementById('whatBar');
        this.whatFeedback = document.getElementById('whatFeedback');
        this.customerFocusBar = document.getElementById('customerFocusBar');
        this.customerFocusValue = document.getElementById('customerFocusValue');
        this.customerFocusFeedback = document.getElementById('customerFocusFeedback');
        this.improvedValueProp = document.getElementById('improvedValueProp');

        this.bindEvents();
    }

    bindEvents() {
        this.analyzeBtn.addEventListener('click', () => this.analyzeValueProp());
    }

    async analyzeValueProp() {
        const target = this.targetCustomer.value.trim();
        const valueProp = this.valueProposition.value.trim();

        if (!valueProp) {
            alert('Please enter your value proposition.');
            return;
        }

        this.setLoading(true);

        try {
            const resp = await fetch('/value-prop/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    value_prop: valueProp,
                    target_customer: target || ''
                })
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || 'Failed to analyze value proposition');
            }

            const data = await resp.json();
            this.displayResults(data);

        } catch (error) {
            console.error('Error analyzing value proposition:', error);
            alert('Failed to analyze value proposition: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }

    displayResults(data) {
        // Overall score
        this.vpOverallScore.textContent = data.overall_score;

        // Golden Circle elements - backend uses golden_circle_analysis with flat fields
        const gcAnalysis = data.golden_circle_analysis || data.golden_circle || {};
        const gcElements = [
            { key: 'why', status: this.whyStatus, bar: this.whyBar, feedback: this.whyFeedback },
            { key: 'how', status: this.howStatus, bar: this.howBar, feedback: this.howFeedback },
            { key: 'what', status: this.whatStatus, bar: this.whatBar, feedback: this.whatFeedback }
        ];

        for (const elem of gcElements) {
            // Try nested structure first, then flat structure
            const nestedData = gcAnalysis[elem.key];
            const score = nestedData?.score ?? gcAnalysis[`${elem.key}_score`] ?? 0;
            const feedback = nestedData?.feedback ?? gcAnalysis[`${elem.key}_feedback`] ?? '';

            let strengthClass;
            if (score >= 8) strengthClass = 'strong';
            else if (score >= 5) strengthClass = 'medium';
            else if (score > 0) strengthClass = 'weak';
            else strengthClass = 'missing';

            elem.status.className = `gc-status ${strengthClass}`;
            elem.status.textContent = strengthClass.charAt(0).toUpperCase() + strengthClass.slice(1);

            elem.bar.className = `gc-fill ${strengthClass}`;
            elem.bar.style.width = `${score * 10}%`;

            elem.feedback.textContent = feedback;
        }

        // Customer focus - backend uses customer_centricity object
        const customerCentricity = data.customer_centricity || {};
        const focusPercent = customerCentricity.score ?? data.customer_focus ?? 0;
        this.customerFocusBar.style.width = `${focusPercent}%`;
        this.customerFocusValue.textContent = `${focusPercent}%`;

        let focusFeedback = customerCentricity.feedback || data.customer_focus_feedback || '';
        if (!focusFeedback) {
            if (focusPercent < 30) focusFeedback = 'Too feature-heavy. Focus more on customer outcomes.';
            else if (focusPercent < 50) focusFeedback = 'Could be more customer-centric.';
            else if (focusPercent < 70) focusFeedback = 'Good balance of features and benefits.';
            else focusFeedback = 'Excellent customer focus!';
        }
        this.customerFocusFeedback.textContent = focusFeedback;

        // Improved version
        if (data.improved_version) {
            this.improvedValueProp.textContent = data.improved_version;
            this.improvedValueProp.parentElement.style.display = 'block';
        } else {
            this.improvedValueProp.parentElement.style.display = 'none';
        }

        this.resultsPanel.classList.remove('hidden');
    }

    setLoading(loading) {
        this.analyzeBtn.disabled = loading;
        this.analyzeBtn.textContent = loading ? 'Analyzing...' : 'Analyze Value Prop';
    }
}

// ========================================
// Navigate Tab - Opportunity Navigator
// ========================================
class NavigateApp {
    constructor() {
        this.salesStage = document.getElementById('salesStage');
        this.navContext = document.getElementById('navContext');
        this.getRecommendationBtn = document.getElementById('getRecommendationBtn');
        this.resultsPanel = document.getElementById('navigateResults');

        // Result elements
        this.nextAction = document.getElementById('nextAction');
        this.actionUrgency = document.getElementById('actionUrgency');
        this.actionTiming = document.getElementById('actionTiming');
        this.prepSteps = document.getElementById('prepSteps');
        this.questionsToAsk = document.getElementById('questionsToAsk');
        this.redFlags = document.getElementById('redFlags');

        this.bindEvents();
        this.loadStages();
    }

    bindEvents() {
        this.getRecommendationBtn.addEventListener('click', () => this.getRecommendation());
    }

    async loadStages() {
        try {
            const resp = await fetch('/navigation/stages');
            if (!resp.ok) throw new Error('Failed to load stages');
            const data = await resp.json();

            this.salesStage.innerHTML = '<option value="">Select a stage...</option>' +
                data.stages.map(stage =>
                    `<option value="${stage.stage}">${this.escapeHtml(stage.stage)}</option>`
                ).join('');
        } catch (error) {
            console.error('Error loading stages:', error);
            // Fallback stages
            const defaultStages = [
                'prospecting', 'discovery', 'qualification', 'demo',
                'proposal', 'negotiation', 'closing', 'won', 'lost'
            ];
            this.salesStage.innerHTML = '<option value="">Select a stage...</option>' +
                defaultStages.map(stage =>
                    `<option value="${stage}">${stage.charAt(0).toUpperCase() + stage.slice(1)}</option>`
                ).join('');
        }
    }

    async getRecommendation() {
        const stage = this.salesStage.value;
        const context = this.navContext.value.trim();

        if (!stage) {
            alert('Please select a sales stage.');
            return;
        }

        this.setLoading(true);

        try {
            const resp = await fetch('/navigation/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_stage: stage,
                    notes: context
                })
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || 'Failed to get recommendation');
            }

            const data = await resp.json();
            this.displayResults(data);

        } catch (error) {
            console.error('Error getting recommendation:', error);
            alert('Failed to get recommendation: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }

    displayResults(data) {
        // Next action - backend returns nested recommended_action object
        const recommendedAction = data.recommended_action || {};
        this.nextAction.textContent = recommendedAction.action || data.next_action || 'No specific action recommended';
        this.actionUrgency.textContent = recommendedAction.urgency || data.urgency || 'Medium';
        this.actionTiming.textContent = recommendedAction.timing || data.timing || 'This week';

        // Preparation steps - backend uses preparation_items
        const prepItems = data.preparation_items || data.preparation || [];
        if (prepItems.length > 0) {
            this.prepSteps.innerHTML = prepItems.map(s =>
                `<li>${this.escapeHtml(s)}</li>`
            ).join('');
            this.prepSteps.parentElement.style.display = 'block';
        } else {
            this.prepSteps.parentElement.style.display = 'none';
        }

        // Questions to ask - backend uses questions_to_ask
        const questions = data.questions_to_ask || data.questions || [];
        if (questions.length > 0) {
            this.questionsToAsk.innerHTML = questions.map(q =>
                `<li>${this.escapeHtml(q)}</li>`
            ).join('');
            this.questionsToAsk.parentElement.style.display = 'block';
        } else {
            this.questionsToAsk.parentElement.style.display = 'none';
        }

        // Red flags
        if (data.red_flags && data.red_flags.length > 0) {
            this.redFlags.innerHTML = data.red_flags.map(r =>
                `<li>${this.escapeHtml(r)}</li>`
            ).join('');
            this.redFlags.parentElement.style.display = 'block';
        } else {
            this.redFlags.parentElement.style.display = 'none';
        }

        this.resultsPanel.classList.remove('hidden');
    }

    setLoading(loading) {
        this.getRecommendationBtn.disabled = loading;
        this.getRecommendationBtn.textContent = loading ? 'Getting Recommendation...' : 'Get Recommendation';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ========================================
// Q&A Tab - RAG Knowledge Base
// ========================================
class QAApp {
    constructor() {
        this.qaQuestion = document.getElementById('qaQuestion');
        this.askBtn = document.getElementById('askQuestionBtn');
        this.resultsPanel = document.getElementById('qaResults');
        this.documentList = document.getElementById('documentList');
        this.fileUpload = document.getElementById('fileUpload');
        this.uploadBtn = document.getElementById('uploadBtn');

        // Result elements
        this.qaAnswer = document.getElementById('qaAnswer');
        this.qaSources = document.getElementById('qaSources');

        this.bindEvents();
        this.loadDocuments();
    }

    bindEvents() {
        this.askBtn.addEventListener('click', () => this.askQuestion());
        this.qaQuestion.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.askQuestion();
            }
        });
        this.uploadBtn.addEventListener('click', () => this.fileUpload.click());
        this.fileUpload.addEventListener('change', (e) => this.uploadDocument(e));
    }

    async loadDocuments() {
        try {
            const resp = await fetch('/rag/documents');
            if (!resp.ok) throw new Error('Failed to load documents');
            const data = await resp.json();

            if (data.documents && data.documents.length > 0) {
                this.documentList.innerHTML = data.documents.map(doc => `
                    <div class="document-item">
                        <div class="document-icon">TXT</div>
                        <span class="document-name">${this.escapeHtml(doc.name || doc)}</span>
                    </div>
                `).join('');
            } else {
                this.documentList.innerHTML = '<div class="loading">No documents in knowledge base</div>';
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            this.documentList.innerHTML = '<div class="error">Failed to load documents</div>';
        }
    }

    async askQuestion() {
        const question = this.qaQuestion.value.trim();

        if (!question) {
            alert('Please enter a question.');
            return;
        }

        this.setLoading(true);

        try {
            const resp = await fetch('/rag/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question })
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || 'Failed to get answer');
            }

            const data = await resp.json();
            this.displayResults(data);

        } catch (error) {
            console.error('Error asking question:', error);
            alert('Failed to get answer: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }

    displayResults(data) {
        // Answer
        this.qaAnswer.textContent = data.answer || 'No answer available';

        // Sources
        if (data.sources && data.sources.length > 0) {
            this.qaSources.innerHTML = data.sources.map(source => {
                const sourceName = typeof source === 'string' ? source : source.source || source.document || source.name;
                const pageInfo = source.page ? ` (page ${source.page})` : '';
                return `<li>${this.escapeHtml(sourceName)}${pageInfo}</li>`;
            }).join('');
            this.qaSources.parentElement.style.display = 'block';
        } else {
            this.qaSources.parentElement.style.display = 'none';
        }

        this.resultsPanel.classList.remove('hidden');
    }

    async uploadDocument(event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        this.uploadBtn.disabled = true;
        this.uploadBtn.textContent = 'Uploading...';

        try {
            const resp = await fetch('/rag/ingest', {
                method: 'POST',
                body: formData
            });

            if (!resp.ok) {
                const error = await resp.json();
                throw new Error(error.detail || 'Failed to upload document');
            }

            alert('Document uploaded successfully!');
            this.loadDocuments();

        } catch (error) {
            console.error('Error uploading document:', error);
            alert('Failed to upload document: ' + error.message);
        } finally {
            this.uploadBtn.disabled = false;
            this.uploadBtn.textContent = 'Upload Document';
            this.fileUpload.value = '';
        }
    }

    setLoading(loading) {
        this.askBtn.disabled = loading;
        this.askBtn.textContent = loading ? 'Asking...' : 'Ask';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ========================================
// Initialize on page load
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize tab manager
    window.tabManager = new TabManager();

    // Initialize all app modules
    window.chatApp = new ChatApp();
    window.questionsApp = new QuestionsApp();
    window.qualifyApp = new QualifyApp();
    window.valuePropApp = new ValuePropApp();
    window.navigateApp = new NavigateApp();
    window.qaApp = new QAApp();
});
