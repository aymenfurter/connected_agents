from flask import Flask, jsonify, render_template_string, send_from_directory
import asyncio
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import threading
import queue
import random

from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import (
    AzureAIAgent,
    AzureAIAgentSettings,
    AzureAIAgentThread,
    GroupChatOrchestration,
    RoundRobinGroupChatManager,
    BooleanResult,
)
from azure.ai.agents.models import ConnectedAgentTool
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.contents import ChatMessageContent, ChatHistory
from azure.ai.projects.aio import AIProjectClient
from azure.ai.agents.models import FilePurpose, FileSearchTool, ToolResources

# Import agent instructions and custom manager from main.py
from main import (
    CRITIC_AGENT_INSTRUCTIONS,
    RECRUITER_AGENT_INSTRUCTIONS,
    JOB_POSTING_AGENT_INSTRUCTIONS,
    SCREENING_AGENT_INSTRUCTIONS,
    CustomGroupChatManager,
    RESUME_NAMES
)

app = Flask(__name__)
load_dotenv()

# Global queue for SSE messages
message_queue = queue.Queue()

class AgentWorkflow:
    def __init__(self):
        self.status = "idle"
        self.messages = []
        self.agents_created = []
        self.vector_stores = []
        self.credential = None
        self.project_client = None
        
        # Agent statistics tracking
        self.agent_stats = {}
        self.workflow_start_time = None
        
    async def run_workflow(self):
        """Run the complete agent workflow"""
        self.status = "running"
        self.workflow_start_time = datetime.now()
        self.add_message("system", "Starting agent workflow...")
        
        try:
            endpoint = os.environ["AZURE_AI_AGENT_ENDPOINT"]
            deployment_name = os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"]
            
            # Create credential and client that will persist for the entire workflow
            self.credential = DefaultAzureCredential()
            self.project_client = AIProjectClient(endpoint=endpoint, credential=self.credential)
            
            # Upload files
            self.add_message("system", "Uploading job description PDF...")
            job_desc_file = await self.project_client.agents.files.upload_and_poll(
                file_path="job_description.pdf", 
                purpose=FilePurpose.AGENTS
            )
            
            self.add_message("system", "Uploading resumes...")
            resume_files = []
            for resume_name in RESUME_NAMES[:5]:  # Limit to 5 for demo
                resume_path = os.path.join("resumes", resume_name)
                if os.path.exists(resume_path):
                    file_obj = await self.project_client.agents.files.upload_and_poll(
                        file_path=resume_path,
                        purpose=FilePurpose.AGENTS
                    )
                    resume_files.append(file_obj)
            
            # Create vector stores
            self.add_message("system", "Creating vector store for resumes...")
            resume_file_ids = [f.id for f in resume_files]
            resumes_vector_store = await self.project_client.agents.vector_stores.create_and_poll(
                file_ids=resume_file_ids,
                name="resumes_vector_store"
            )
            self.vector_stores.append(resumes_vector_store.id)
            
            self.add_message("system", "Creating vector store for job description...")
            jd_vector_store = await self.project_client.agents.vector_stores.create_and_poll(
                file_ids=[job_desc_file.id],
                name="job_description_vector_store"
            )
            self.vector_stores.append(jd_vector_store.id)
            
            # Create agents with statistics tracking
            self.add_message("system", "Creating JobPosting agent...")
            jd_file_search_tool = FileSearchTool(vector_store_ids=[jd_vector_store.id])
            workflow_agent_def = await self.project_client.agents.create_agent(
                model=deployment_name,
                name="JobPosting_agent",
                instructions=JOB_POSTING_AGENT_INSTRUCTIONS,
                tools=jd_file_search_tool.definitions,
                tool_resources=ToolResources(file_search={"vector_store_ids": [jd_vector_store.id]})
            )
            self.agents_created.append({
                "name": "JobPosting_agent", 
                "id": workflow_agent_def.id,
                "description": "Analyzes job postings and requirements",
                "tools": ["file_search"],
                "vector_stores": [jd_vector_store.id]
            })
            self.init_agent_stats("JobPosting_agent")
            
            self.add_message("system", "Creating CandidateScreening agent...")
            screening_file_search_tool = FileSearchTool(vector_store_ids=[resumes_vector_store.id])
            screening_agent_def = await self.project_client.agents.create_agent(
                model=deployment_name,
                name="CandidateScreening_agent",
                instructions=SCREENING_AGENT_INSTRUCTIONS,
                tools=screening_file_search_tool.definitions,
                tool_resources=ToolResources(file_search={"vector_store_ids": [resumes_vector_store.id]})
            )
            self.agents_created.append({
                "name": "CandidateScreening_agent", 
                "id": screening_agent_def.id,
                "description": "Evaluates candidate resumes against job requirements",
                "tools": ["file_search"],
                "vector_stores": [resumes_vector_store.id]
            })
            self.init_agent_stats("CandidateScreening_agent")
            
            self.add_message("system", "Creating Recruiter agent...")
            workflow_tool = ConnectedAgentTool(
                id=workflow_agent_def.id, 
                name="JobPosting_agent", 
                description="Summarizes the job posting."
            )
            screening_tool = ConnectedAgentTool(
                id=screening_agent_def.id, 
                name="CandidateScreening_agent", 
                description="Screens a candidate's CV against a job description."
            )
            recruiter_agent_def = await self.project_client.agents.create_agent(
                model=deployment_name,
                name="recruiter",
                instructions=RECRUITER_AGENT_INSTRUCTIONS,
                temperature=0.1,
                tools=[screening_tool.definitions[0], workflow_tool.definitions[0]],
            )
            self.agents_created.append({
                "name": "recruiter", 
                "id": recruiter_agent_def.id,
                "description": "Orchestrates the recruitment workflow",
                "tools": ["connected_agent.JobPosting_agent", "connected_agent.CandidateScreening_agent"],
                "vector_stores": []
            })
            self.init_agent_stats("recruiter")
            
            self.add_message("system", "Creating Workflow critic agent...")
            critic_agent_def = await self.project_client.agents.create_agent(
                model=deployment_name,
                name="workflow",
                temperature=0.1,
                instructions=CRITIC_AGENT_INSTRUCTIONS,
            )
            self.agents_created.append({
                "name": "workflow", 
                "id": critic_agent_def.id,
                "description": "Guides and critiques the recruitment process",
                "tools": [],
                "vector_stores": []
            })
            self.init_agent_stats("workflow")
            
            # Create agent instances
            critic_agent = AzureAIAgent(
                client=self.project_client,
                definition=critic_agent_def,
                description="Asks questions to identify the best candidates for the job posting."
            )
            recruiter_agent = AzureAIAgent(
                client=self.project_client,
                definition=recruiter_agent_def,
                description="Recruiter agent with access to candidate data."
            )
            
            # Agent response callback with timing
            def agent_response_callback(message: ChatMessageContent) -> None:
                content = str(message.content)
                agent_name = message.name or message.role
                
                # Track agent invocation for ALL agents (including critic and recruiter)
                self.track_agent_invocation(agent_name, content)
                
                # Detect tool usage for better visualization
                if "connected_agent" in content:
                    content = f"[DELEGATION] {content}"
                    print (f"Agent {agent_name} delegated task: {content}")
                elif "myfiles_browser" in content or "file_search" in content:
                    content = f"[SEARCH] {content}"
                
                self.add_message(
                    agent_name,
                    content,
                    agent_type=agent_name
                )
            
            # Set up group chat
            agents = [recruiter_agent, critic_agent]
            group_chat_orchestration = GroupChatOrchestration(
                members=agents,
                manager=CustomGroupChatManager(max_rounds=10),
                agent_response_callback=agent_response_callback,
            )
            
            # Start runtime
            runtime = InProcessRuntime()
            runtime.start()
            
            # Run orchestration
            self.add_message("system", "Starting group chat...")
            kickoff_message = "Please provide a summary of the job posting. (using myfiles_browser)"
            
            orchestration_result = await group_chat_orchestration.invoke(
                task=kickoff_message,
                runtime=runtime,
            )
            
            value = await orchestration_result.get()
            self.add_message("system", f"Workflow completed: {value}")
            
            await runtime.stop_when_idle()
            
            self.status = "completed"
            
        except Exception as e:
            self.status = "error"
            self.add_message("error", f"Error: {str(e)}")
        finally:
            # Clean up resources
            if self.project_client:
                await self.project_client.close()
                self.project_client = None
            if self.credential:
                await self.credential.close()
                self.credential = None
    
    def init_agent_stats(self, agent_name):
        """Initialize statistics for an agent"""
        self.agent_stats[agent_name] = {
            "invocations": 0,
            "total_response_time": 0,
            "avg_response_time": 0,
            "first_invocation": None,
            "last_invocation": None,
            "messages": []
        }
    
    def track_agent_invocation(self, agent_name, content):
        """Track agent invocation statistics"""
        # Initialize stats for any agent that sends a message (including critic/recruiter)
        if agent_name not in self.agent_stats:
            self.init_agent_stats(agent_name)
        
        now = datetime.now()
        stats = self.agent_stats[agent_name]
        
        stats["invocations"] += 1
        stats["last_invocation"] = now
        if stats["first_invocation"] is None:
            stats["first_invocation"] = now
        
        # Simple response time simulation (in real scenario, track actual timing)
        response_time = len(content) * 0.01 + random.uniform(0.5, 2.0)  # Simulate based on content length
        stats["total_response_time"] += response_time
        stats["avg_response_time"] = stats["total_response_time"] / stats["invocations"]
        
        stats["messages"].append({
            "timestamp": now.isoformat(),
            "content_length": len(content),
            "response_time": response_time
        })
            
    def add_message(self, sender, content, agent_type=None):
        """Add a message and notify SSE clients"""
        message = {
            "timestamp": datetime.now().isoformat(),
            "sender": sender,
            "content": content,
            "agent_type": agent_type or sender
        }
        self.messages.append(message)
        message_queue.put(json.dumps(message))

# Global workflow instance
workflow = AgentWorkflow()

@app.route('/')
def index():
    """Serve the frontend"""
    return send_from_directory('ui', 'index.html')

@app.route('/ui/<path:path>')
def send_ui(path):
    """Serve UI files"""
    return send_from_directory('ui', path)

@app.route('/api/status')
def get_status():
    """Get current workflow status"""
    return jsonify({
        "status": workflow.status,
        "messages": workflow.messages,
        "agents": workflow.agents_created,
        "vector_stores": workflow.vector_stores
    })

@app.route('/api/start', methods=['POST'])
def start_workflow():
    """Start the agent workflow"""
    if workflow.status == "running":
        return jsonify({"error": "Workflow already running"}), 400
    
    # Reset workflow
    workflow.status = "idle"
    workflow.messages = []
    workflow.agents_created = []
    workflow.vector_stores = []
    
    # Run workflow in background
    def run_async_workflow():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(workflow.run_workflow())
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_async_workflow)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/events')
def events():
    """Server-sent events for real-time updates"""
    def generate():
        while True:
            try:
                message = message_queue.get(timeout=1)
                yield f"data: {message}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return app.response_class(
        generate(),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/api/agent/<agent_name>')
def get_agent_details(agent_name):
    """Get detailed information about a specific agent"""
    # First check if it's one of the pre-created agents
    agent_info = None
    for agent in workflow.agents_created:
        if agent["name"] == agent_name:
            agent_info = agent
            break
    
    # If not found in pre-created agents, check if it's critic or recruiter
    if not agent_info and agent_name in ["workflow", "recruiter"]:
        # Create agent info for critic/recruiter based on their names
        if agent_name == "workflow":
            agent_info = {
                "name": "workflow",
                "id": "critic-agent-id",  # In real scenario, get actual ID
                "description": "Guides and critiques the recruitment process",
                "tools": [],
                "vector_stores": []
            }
        elif agent_name == "recruiter":
            agent_info = {
                "name": "recruiter", 
                "id": "recruiter-agent-id",  # In real scenario, get actual ID
                "description": "Orchestrates the recruitment workflow",
                "tools": ["connected_agent.JobPosting_agent", "connected_agent.CandidateScreening_agent"],
                "vector_stores": []
            }
    
    if not agent_info:
        return jsonify({"error": "Agent not found"}), 404
    
    stats = workflow.agent_stats.get(agent_name, {})
    
    # Calculate additional metrics
    total_time = None
    if workflow.workflow_start_time and stats.get("last_invocation"):
        if isinstance(stats["last_invocation"], str):
            last_invocation = datetime.fromisoformat(stats["last_invocation"])
        else:
            last_invocation = stats["last_invocation"]
        total_time = (last_invocation - workflow.workflow_start_time).total_seconds()
    
    playground_url = None
    if os.environ.get("AZURE_PLAYGROUND_URL_PREFIX") and agent_info["id"] != "critic-agent-id" and agent_info["id"] != "recruiter-agent-id":
        playground_url = f"{os.environ['AZURE_PLAYGROUND_URL_PREFIX']}{agent_info['id']}"
    
    return jsonify({
        "name": agent_info["name"],
        "id": agent_info["id"],
        "description": agent_info["description"],
        "tools": agent_info["tools"],
        "vector_stores": agent_info["vector_stores"],
        "playground_url": playground_url,
        "statistics": {
            "invocations": stats.get("invocations", 0),
            "avg_response_time": round(stats.get("avg_response_time", 0), 2),
            "total_response_time": round(stats.get("total_response_time", 0), 2),
            "first_invocation": stats.get("first_invocation").isoformat() if stats.get("first_invocation") else None,
            "last_invocation": stats.get("last_invocation").isoformat() if stats.get("last_invocation") else None,
            "total_workflow_time": round(total_time, 2) if total_time else None
        },
        "messages": stats.get("messages", [])[-5:]  # Last 5 messages
    })

@app.route('/api/config')
def get_config():
    """Get configuration for the frontend"""
    return jsonify({
        "playground_url_prefix": os.environ.get("AZURE_PLAYGROUND_URL_PREFIX", ""),
        "azure_endpoint": os.environ.get("AZURE_AI_AGENT_ENDPOINT", ""),
        "model_deployment": os.environ.get("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME", "")
    })

if __name__ == '__main__':
    os.makedirs('ui', exist_ok=True)
    app.run(debug=True, port=5000)
