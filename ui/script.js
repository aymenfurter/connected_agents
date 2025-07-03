// filepath: /workspaces/connected_agents/ui/script.js
class AgentWorkflowUI {
    constructor() {
        this.startBtn = document.getElementById('startBtn');
        this.messagesContainer = document.getElementById('messagesContainer');
        this.resultsSection = document.getElementById('resultsSection');
        this.resultsContainer = document.getElementById('resultsContainer');
        this.statusIndicator = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.statusInfo = document.getElementById('statusInfo');
        this.networkContainer = document.getElementById('agent-network');
        
        this.eventSource = null;
        this.network = null;
        this.nodes = new vis.DataSet();
        this.edges = new vis.DataSet();
        this.lastActiveAgent = null;
        this.delegationEdges = new Map();
        
        // Step tracking
        this.steps = [];
        this.currentStep = -1;
        this.isReplayMode = false;
        
        // Define consistent node shapes
        this.nodeShapes = {
            orchestrator: 'box',      // Main coordinating agents
            specialist: 'diamond',   // Specialized task agents  
            critic: 'ellipse',      // Review/guidance agents
            datastore: 'database'   // Data storage nodes
        };
        
        this.init();
    }
    
    init() {
        this.startBtn.addEventListener('click', () => this.startWorkflow());
        this.setupAgentNetwork();
    }

    setupAgentNetwork() {
        const agentData = [
            { 
                id: 'recruiter', 
                label: 'Recruiter', 
                color: { background: '#162820', border: '#3fb950', highlight: { background: '#1a3525', border: '#4ade80' } }, 
                shape: this.nodeShapes.specialist,
                size: 35,
                font: { size: 14, color: '#c9d1d9', bold: true }
            },
            { 
                id: 'workflow', 
                label: 'Critic', 
                color: { background: '#231d30', border: '#bc8cff', highlight: { background: '#2a2438', border: '#c4b5fd' } }, 
                shape: this.nodeShapes.specialist,
                size: 30,
                font: { size: 12, color: '#c9d1d9' }
            },
            { 
                id: 'JobPosting_agent', 
                label: 'Job Posting', 
                color: { background: '#2a1f16', border: '#f0883e', highlight: { background: '#322419', border: '#fb923c' } }, 
                shape: this.nodeShapes.specialist,
                size: 30,
                font: { size: 12, color: '#c9d1d9' }
            },
            { 
                id: 'CandidateScreening_agent', 
                label: 'Screening', 
                color: { background: '#1a222d', border: '#58a6ff', highlight: { background: '#1e2936', border: '#60a5fa' } }, 
                shape: this.nodeShapes.specialist,
                size: 30,
                font: { size: 12, color: '#c9d1d9' }
            },
            { 
                id: 'job_datastore', 
                label: 'Job Docs', 
                color: { background: '#2a1f16', border: '#f0883e', highlight: { background: '#322419', border: '#fb923c' } }, 
                shape: this.nodeShapes.datastore,
                size: 25,
                font: { size: 10, color: '#8b949e' }
            },
            { 
                id: 'resume_datastore', 
                label: 'Resumes', 
                color: { background: '#1a222d', border: '#58a6ff', highlight: { background: '#1e2936', border: '#60a5fa' } }, 
                shape: this.nodeShapes.datastore,
                size: 25,
                font: { size: 10, color: '#8b949e' }
            }
        ];
        this.nodes.add(agentData);

        // Static edges that will change appearance based on communication
        const staticEdges = [
            // Agent communication links
            {
                id: 'critic-recruiter',
                from: 'workflow',
                to: 'recruiter',
                color: { color: '#484f58' },
                width: 1,
                arrows: { to: { enabled: false, scaleFactor: 0.7 } }
            },
            {
                id: 'recruiter-jobposting',
                from: 'recruiter',
                to: 'JobPosting_agent',
                color: { color: '#484f58' },
                width: 1,
                arrows: { to: { enabled: true, scaleFactor: 0.7 } }
            },
            {
                id: 'recruiter-screening',
                from: 'recruiter',
                to: 'CandidateScreening_agent',
                color: { color: '#484f58' },
                width: 1,
                arrows: { to: { enabled: true, scaleFactor: 0.7 } }
            },
            // Data store connections
            {
                id: 'job-to-datastore',
                from: 'JobPosting_agent',
                to: 'job_datastore',
                color: { color: '#f0883e', opacity: 0.4 },
                width: 2,
                dashes: [3, 3],
                arrows: { to: { enabled: false } }
            },
            {
                id: 'screening-to-datastore',
                from: 'CandidateScreening_agent',
                to: 'resume_datastore',
                color: { color: '#58a6ff', opacity: 0.4 },
                width: 2,
                dashes: [3, 3],
                arrows: { to: { enabled: false } }
            }
        ];
        this.edges.add(staticEdges);

        const data = { nodes: this.nodes, edges: this.edges };
        const options = {
            nodes: {
                font: { 
                    color: '#c9d1d9', 
                    face: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif",
                    background: 'transparent',
                    strokeWidth: 0,
                    strokeColor: 'transparent'
                },
                borderWidth: 2,
                shadow: false,
                shapeProperties: { 
                    interpolation: false,
                    useImageSize: false
                },
                // Ensure consistent rendering
                chosen: {
                    node: (values, id, selected, hovering) => {
                        values.borderWidth = selected ? 4 : 2;
                    }
                }
            },
            edges: {
                width: 2,
                smooth: { type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.4 },
                arrows: { to: { enabled: true, scaleFactor: 0.7 } },
                color: { color: '#484f58', highlight: '#58a6ff', hover: '#58a6ff' },
                font: { 
                    size: 9, 
                    color: '#8b949e', 
                    background: 'rgba(13, 17, 23, 0.8)',
                    strokeWidth: 0,
                    strokeColor: 'transparent'
                },
                shadow: false
            },
            physics: {
                enabled: true,
                solver: 'barnesHut',
                barnesHut: { 
                    gravitationalConstant: -8000, 
                    springLength: 180, 
                    springConstant: 0.04,
                    damping: 0.09
                },
                stabilization: { iterations: 200 }
            },
            interaction: {
                dragNodes: true,
                hover: true,
                tooltipDelay: 300
            },
            layout: {
                hierarchical: false,
                randomSeed: 42
            },
            configure: { enabled: false }
        };
        
        this.network = new vis.Network(this.networkContainer, data, options);
        
        this.network.on('click', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                if (!nodeId.includes('_datastore')) {
                    this.showAgentDetails(nodeId);
                }
            }
        });
        
        this.network.on('afterDrawing', () => {
            const canvas = this.networkContainer.querySelector('canvas');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.globalCompositeOperation = 'destination-over';
                ctx.fillStyle = '#21262d';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.globalCompositeOperation = 'source-over';
            }
        });
        
        const loader = this.networkContainer.querySelector('.network-loader');
        if (loader) {
            loader.style.display = 'none';
        }
    }
    
    async startWorkflow() {
        if (this.startBtn.classList.contains('loading')) return;
        
        this.startBtn.classList.add('loading');
        this.startBtn.innerHTML = '<span class="icon">⏳</span> Running...';
        this.messagesContainer.innerHTML = '';
        this.resultsSection.style.display = 'none';
        this.lastActiveAgent = null;
        
        this.steps = [];
        this.currentStep = -1;
        this.isReplayMode = false;
        
        // Reset communication edges to default state (don't remove them)
        this.edges.update({ id: 'critic-recruiter', color: { color: '#484f58' }, width: 1 });
        this.edges.update({ id: 'recruiter-jobposting', color: { color: '#484f58' }, width: 1 });
        this.edges.update({ id: 'recruiter-screening', color: { color: '#484f58' }, width: 1 });
        
        this.delegationEdges.clear();
        
        this.nodes.getIds().forEach(id => this.nodes.update({ id, borderWidth: 2 }));
        
        try {
            const response = await fetch('/api/start', { method: 'POST' });
            const data = await response.json();
            
            if (response.ok) {
                this.updateStatus('Running', 'active');
                this.connectToEventStream();
            } else {
                this.showError(data.error || 'Failed to start workflow');
            }
        } catch (error) {
            this.showError(`Error: ${error.message}`);
        }
    }
    
    connectToEventStream() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        this.eventSource = new EventSource('/api/events');
        
        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type !== 'heartbeat') {
                this.handleMessage(data);
            }
        };
        
        this.eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            this.eventSource.close();
            this.checkWorkflowStatus();
        };
    }
    
    handleMessage(data) {
        this.addMessage(data);
        
        if (data.agent_type && data.agent_type !== 'system' && data.agent_type !== 'error') {
            this.setAgentActive(data.agent_type);
            this.highlightCommunication(data.agent_type);
        }
        
        if (data.content && data.content.includes('COMPLETED')) {
            this.handleCompletion(data);
        }
        
        this.updateStatusInfo(data);
    }
    
    addMessage(data) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${data.agent_type}`;
        messageDiv.dataset.stepId = this.steps.length;
        
        const time = new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-sender ${data.agent_type}">${data.sender}</span>
                <span class="message-time">${time}</span>
                <span class="step-indicator">Step ${this.steps.length + 1}</span>
            </div>
            <div class="message-content">${this.formatContent(data.content)}</div>
        `;
        
        messageDiv.addEventListener('click', () => this.showStepState(parseInt(messageDiv.dataset.stepId)));
        
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        
        // Initial step state capture (will be updated after delegation detection)
        this.captureStepState(data);
    }
    
    highlightCommunication(agentType) {
        // Reset all communication edges to default
        this.edges.update({ id: 'critic-recruiter', color: { color: '#484f58' }, width: 1 });
        this.edges.update({ id: 'recruiter-jobposting', color: { color: '#484f58' }, width: 1 });
        this.edges.update({ id: 'recruiter-screening', color: { color: '#484f58' }, width: 1 });
        
        // Highlight the active communication path
        if (agentType === 'workflow') {
            this.edges.update({ 
                id: 'critic-recruiter', 
                color: { color: '#bc8cff' }, 
                width: 3 
            });
        } else if (agentType === 'recruiter') {
            this.edges.update({ 
                id: 'critic-recruiter', 
                color: { color: '#3fb950' }, 
                width: 3 
            });
        } else if (agentType === 'JobPosting_agent') {
            this.edges.update({ 
                id: 'recruiter-jobposting', 
                color: { color: '#f0883e' }, 
                width: 3 
            });
        } else if (agentType === 'CandidateScreening_agent') {
            this.edges.update({ 
                id: 'recruiter-screening', 
                color: { color: '#58a6ff' }, 
                width: 3 
            });
        }
        
        // Reset highlighting after a delay
        setTimeout(() => {
            if (!this.isReplayMode) {
                this.edges.update({ id: 'critic-recruiter', color: { color: '#484f58' }, width: 1 });
                this.edges.update({ id: 'recruiter-jobposting', color: { color: '#484f58' }, width: 1 });
                this.edges.update({ id: 'recruiter-screening', color: { color: '#484f58' }, width: 1 });
            }
        }, 2000);
    }

    captureStepState(data) {
        const stepState = {
            message: data,
            activeAgent: data.agent_type,
            // Only capture the communication edges state
            edgeStates: {
                'critic-recruiter': this.edges.get('critic-recruiter'),
                'recruiter-jobposting': this.edges.get('recruiter-jobposting'),
                'recruiter-screening': this.edges.get('recruiter-screening')
            },
            nodeStates: this.nodes.get().map(node => ({
                id: node.id,
                borderWidth: node.borderWidth || 2,
                shadow: node.shadow || false
            })),
            timestamp: new Date().toISOString()
        };
        
        this.steps.push(stepState);
        this.currentStep = this.steps.length - 1;
    }
    
    updateCurrentStepState() {
        if (this.steps.length === 0) return;
        
        const currentStep = this.steps[this.steps.length - 1];
        currentStep.edgeStates = {
            'critic-recruiter': this.edges.get('critic-recruiter'),
            'recruiter-jobposting': this.edges.get('recruiter-jobposting'),
            'recruiter-screening': this.edges.get('recruiter-screening')
        };
        currentStep.nodeStates = this.nodes.get().map(node => ({
            id: node.id,
            borderWidth: node.borderWidth || 2,
            shadow: node.shadow || false
        }));
        currentStep.activeAgent = this.lastActiveAgent;
    }
    
    showStepState(stepId) {
        if (stepId < 0 || stepId >= this.steps.length) return;
        
        this.isReplayMode = true;
        this.currentStep = stepId;
        const step = this.steps[stepId];
        
        document.querySelectorAll('.message').forEach(msg => msg.classList.remove('selected'));
        
        const selectedMessage = document.querySelector(`[data-step-id="${stepId}"]`);
        if (selectedMessage) {
            selectedMessage.classList.add('selected');
        }
        
        this.restoreNetworkState(step);
        this.updateStatusInfo({ content: `Viewing Step ${stepId + 1}: ${step.message.sender}` });
        this.showReplayModeIndicator(stepId);
    }
    
    restoreNetworkState(step) {
        // Restore edge states
        if (step.edgeStates) {
            Object.keys(step.edgeStates).forEach(edgeId => {
                const edgeState = step.edgeStates[edgeId];
                if (edgeState) {
                    this.edges.update({
                        id: edgeId,
                        color: edgeState.color,
                        width: edgeState.width
                    });
                }
            });
        }
        
        // Restore node states
        step.nodeStates.forEach(nodeState => {
            this.nodes.update({
                id: nodeState.id,
                borderWidth: nodeState.borderWidth,
                shadow: nodeState.shadow
            });
        });
        
        // Highlight the communication for this step
        if (step.activeAgent) {
            this.highlightCommunication(step.activeAgent);
        }
    }
    
    showReplayModeIndicator(stepId) {
        const existingIndicator = document.querySelector('.replay-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        const step = this.steps[stepId];
        const delegationCount = step.edges ? step.edges.filter(e => e.id.includes('delegation')).length : 0;
        
        const indicator = document.createElement('div');
        indicator.className = 'replay-indicator';
        indicator.innerHTML = `
            <div class="replay-content">
                <span>📍 Step ${stepId + 1}/${this.steps.length}</span>
                ${delegationCount > 0 ? `<span class="delegation-count">🔗 ${delegationCount} delegations</span>` : ''}
                <button class="replay-exit">Exit Replay</button>
            </div>
        `;
        
        this.networkContainer.appendChild(indicator);
        
        indicator.querySelector('.replay-exit').addEventListener('click', () => this.exitReplayMode());
    }
    
    exitReplayMode() {
        this.isReplayMode = false;
        this.currentStep = this.steps.length - 1;
        
        document.querySelectorAll('.message').forEach(msg => msg.classList.remove('selected'));
        
        if (this.steps.length > 0) {
            this.restoreNetworkState(this.steps[this.steps.length - 1]);
        }
        
        const indicator = document.querySelector('.replay-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    handleCompletion(data) {
        const content = data.content;
        if (content.includes('candidates') && content.includes('|')) {
            this.showResults(content);
        }
        
        setTimeout(() => {
            this.checkWorkflowStatus();
        }, 2000);
    }

    formatContent(content) {
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/connected_agent\.(\w+)/g, '<span class="tool-call">🔗 $1</span>');
        content = content.replace(/myfiles_browser/g, '<span class="tool-call">📁 File Search</span>');
        
        if (content.includes('|')) {
            const tableRegex = /((?:\|.*\|(?:\r\n|\n))+)/g;
            return content.replace(tableRegex, (match) => this.formatMarkdownTable(match));
        }
        return content;
    }
    
    formatMarkdownTable(tableContent) {
        const lines = tableContent.trim().split('\n').filter(line => line.includes('|'));
        if (lines.length < 2 || !lines[1].includes('---')) return tableContent;

        let tableHtml = '<table>';
        const headerLine = lines[0];
        const headers = headerLine.split('|').slice(1, -1).map(h => h.trim());
        
        tableHtml += '<thead><tr>';
        headers.forEach(h => tableHtml += `<th>${h}</th>`);
        tableHtml += '</tr></thead>';

        tableHtml += '<tbody>';
        lines.slice(2).forEach(line => {
            const cells = line.split('|').slice(1, -1).map(c => c.trim());
            if (cells.length === headers.length && cells.some(c => c)) {
                tableHtml += '<tr>';
                cells.forEach(c => tableHtml += `<td>${c}</td>`);
                tableHtml += '</tr>';
            }
        });
        tableHtml += '</tbody></table>';

        return tableHtml;
    }
    
    showResults(content) {
        this.resultsSection.style.display = 'block';
        this.resultsContainer.innerHTML = this.formatContent(content.split('COMPLETED')[0]);
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
    
    async checkWorkflowStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.status === 'completed' || data.status === 'error') {
                this.updateStatus(data.status.charAt(0).toUpperCase() + data.status.slice(1), data.status);
                this.startBtn.classList.remove('loading');
                this.startBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Start Workflow';
                
                if (this.eventSource) {
                    this.eventSource.close();
                }
                
                if (this.lastActiveAgent) {
                    this.nodes.update({ id: this.lastActiveAgent, borderWidth: 2 });
                    this.lastActiveAgent = null;
                }
            }
        } catch (error) {
            console.error('Error checking status:', error);
        }
    }
    
    updateStatus(text, state) {
        this.statusText.textContent = text;
        this.statusIndicator.className = 'status-dot';
        
        if (state === 'active' || state === 'running') {
            this.statusIndicator.classList.add('active');
        } else if (state === 'error') {
            this.statusIndicator.style.background = '#f85149';
        }
    }
    
    updateStatusInfo(data) {
        if (data.agent_type === 'system') {
            this.statusInfo.textContent = data.content.substring(0, 80) + '...';
        }
    }
    
    showError(message) {
        this.updateStatus('Error', 'error');
        this.startBtn.classList.remove('loading');
        this.startBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Start Workflow';
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message error';
        errorDiv.innerHTML = `
            <div class="message-header">
                <span class="message-sender error">Error</span>
                <span class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <div class="message-content">${message}</div>
        `;
        
        this.messagesContainer.appendChild(errorDiv);
    }
    
    async showAgentDetails(agentName) {
        try {
            const response = await fetch(`/api/agent/${agentName}`);
            if (!response.ok) {
                console.error('Failed to fetch agent details');
                return;
            }
            
            const agentData = await response.json();
            this.displayAgentModal(agentData);
        } catch (error) {
            console.error('Error fetching agent details:', error);
        }
    }
    
    displayAgentModal(agentData) {
        const existingModal = document.querySelector('.agent-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        const modal = document.createElement('div');
        modal.className = 'agent-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>${agentData.name}</h2>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="agent-info">
                        <p class="agent-description">${agentData.description}</p>
                        <div class="agent-id">ID: <code>${agentData.id}</code></div>
                    </div>
                    
                    <div class="agent-section">
                        <h3>Tools & Resources</h3>
                        <div class="tools-list">
                            ${agentData.tools.map(tool => `<span class="tool-badge">${tool}</span>`).join('')}
                        </div>
                        ${agentData.vector_stores.length > 0 ? `
                            <div class="vector-stores">
                                <strong>Vector Stores:</strong> ${agentData.vector_stores.length} attached
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="agent-section">
                        <h3>Performance Metrics</h3>
                        <div class="metrics-grid">
                            <div class="metric">
                                <span class="metric-value">${agentData.statistics.invocations}</span>
                                <span class="metric-label">Invocations</span>
                            </div>
                            <div class="metric">
                                <span class="metric-value">${agentData.statistics.avg_response_time}s</span>
                                <span class="metric-label">Avg Response Time</span>
                            </div>
                            <div class="metric">
                                <span class="metric-value">${agentData.statistics.total_response_time}s</span>
                                <span class="metric-label">Total Response Time</span>
                            </div>
                            ${agentData.statistics.total_workflow_time ? `
                                <div class="metric">
                                    <span class="metric-value">${agentData.statistics.total_workflow_time}s</span>
                                    <span class="metric-label">Total Workflow Time</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    
                    ${agentData.statistics.first_invocation ? `
                        <div class="agent-section">
                            <h3>Activity Timeline</h3>
                            <div class="timeline">
                                <div class="timeline-item">
                                    <strong>First Invocation:</strong> ${new Date(agentData.statistics.first_invocation).toLocaleString()}
                                </div>
                                <div class="timeline-item">
                                    <strong>Last Invocation:</strong> ${new Date(agentData.statistics.last_invocation).toLocaleString()}
                                </div>
                            </div>
                        </div>
                    ` : ''}
                    
                    ${agentData.playground_url ? `
                        <div class="agent-section">
                            <h3>Actions</h3>
                            <a href="${agentData.playground_url}" target="_blank" class="playground-link">
                                🚀 Open in Azure AI Playground
                            </a>
                        </div>
                    ` : ''}
                </div>
            </div>
            <div class="modal-overlay"></div>
        `;
        
        document.body.appendChild(modal);
        
        const closeBtn = modal.querySelector('.modal-close');
        const overlay = modal.querySelector('.modal-overlay');
        
        const closeModal = () => modal.remove();
        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', closeModal);
        
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AgentWorkflowUI();
});