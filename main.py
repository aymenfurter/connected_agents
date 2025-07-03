import os
import glob
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

import asyncio

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


CRITIC_AGENT_INSTRUCTIONS = """
Guide the recruiter agent in identifying the best candidates for the job posting.

As soon as you receive the list of candidates (at least 3 names), respond with only the word "COMPLETED".

Never include "Persona XYZ Adopted" in your response. 

Only answer in a single sentence, e.g.
"Please provide a list of 5 candidates that best match the job description. Format as table, include columns with scoring and ranking."
or
"Please rank the candidates based on their suitability for the job posting."

DO NOT answer questions directly. 
"""

RECRUITER_AGENT_INSTRUCTIONS = """
- Never include "Persona XYZ Adopted" in your response. 
- Never answer questions directly. ALWAYS use either the **CandidateScreening_agent** or the **JobPosting_agent** to get the information you need.

## 2. Available Tools
- **connected_agent.CandidateScreening_agent**: Provides job posting information
- **connected_agent.JobPosting_agent**: Evaluates candidate CVs


"""

JOB_POSTING_AGENT_INSTRUCTIONS = """
- Only answer using myfiles_browser tool (Search for 'Requirements' in the job description PDF).
"""

SCREENING_AGENT_INSTRUCTIONS = """
- Never include "Persona XYZ Adopted" in your response. 
- Only answer using myfiles_browser tool
"""

class CustomGroupChatManager(RoundRobinGroupChatManager):
    async def should_terminate(self, chat_history: ChatHistory) -> BooleanResult:
        # Terminate if the last message contains "COMPLETED"
        if chat_history.messages and "COMPLETED" in chat_history.messages[-1].content.upper():
            return BooleanResult(result=True, reason="Termination condition met.")
        
        # Fallback to base class termination logic (e.g., max_rounds)
        return await super().should_terminate(chat_history)

RESUME_NAMES = [
    "Resume_DevOps_Engineer_Alexander_Kumar.pdf",
    "Resume_Software_Architect_Maria_Gonzalez.pdf",
    "Resume_Full_Stack_Dev_Thomas_Chen.pdf",
    "Resume_Product_Manager_Aisha_Patel.pdf",
    "Resume_Data_Scientist_Lucas_Bishop.pdf",
    "Resume_UX_Designer_Nina_Rodriguez.pdf",
    "Resume_ML_Engineer_James_Kim.pdf",
    "Resume_Cloud_Architect_Sarah_OConnor.pdf",
    "Resume_Security_Engineer_Marcus_Singh.pdf",
    "Resume_Program_Manager_Rachel_Zhou.pdf",
    "Resume_Frontend_Dev_Omar_Hassan.pdf",
    "Resume_Backend_Dev_Emma_Thompson.pdf",
    "Resume_QA_Engineer_David_Nguyen.pdf",
    "Resume_Tech_Lead_Sofia_Martinez.pdf",
    "Resume_Systems_Engineer_Michael_Chang.pdf",
]

console = Console()

def check_required_files():
    """Check if all required files exist"""
    missing_files = []
    
    # Check job description
    if not os.path.exists("job_description.pdf"):
        missing_files.append("job_description.pdf")
    
    # Check resumes
    os.makedirs("resumes", exist_ok=True)
    for resume_name in RESUME_NAMES:
        if not os.path.exists(os.path.join("resumes", resume_name)):
            missing_files.append(f"resumes/{resume_name}")
    
    if missing_files:
        console.print("[red]Missing required files:[/red]")
        for f in missing_files:
            console.print(f"  - {f}")
        console.print("\n[yellow]Please run create_data.py to generate missing files.[/yellow]")
        return False
    return True

async def delete_all_agents(project_client, console):
    """Delete all existing agents in the project."""
    try:
        # List all agents
        agents = [agent async for agent in project_client.agents.list_agents()]
        if not agents:
            console.print("[yellow]No existing agents found.[/yellow]")
            return

        console.print(Panel.fit(f"[bold]Found {len(agents)} existing agents to delete...[/bold]", style="cyan"))
        
        # Add confirmation prompt
        console.print("[yellow]Do you want to delete all existing agents? Press 'Y' to confirm or any other key to skip:[/yellow]")
        user_input = input().strip().upper()
        
        if user_input != 'Y':
            console.print("[yellow]Skipping agent deletion.[/yellow]")
            return
            
        for agent in agents:
            try:
                await project_client.agents.delete_agent(agent.id)
                console.print(f"[green]Deleted agent {agent.id}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to delete agent {agent.id}:[/red] {e}")
    except Exception as e:
        console.print(f"[red]Error listing/deleting agents:[/red] {e}")

async def main():
    load_dotenv()
    
    # Check for required files first
    if not check_required_files():
        return

    try:
        endpoint = os.environ["AZURE_AI_AGENT_ENDPOINT"]
        deployment_name = os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"]
    except KeyError as e:
        console.print(f"[red]Error:[/red] Environment variable {e} not set.")
        console.print("[yellow]Please set AZURE_AI_AGENT_ENDPOINT and AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME.[/yellow]")
        return

    # Remove download section and continue with existing code
    async with (
        DefaultAzureCredential() as creds,
        AIProjectClient(endpoint=endpoint, credential=creds) as project_client,
    ):
        # Delete any existing agents before proceeding
        await delete_all_agents(project_client, console)

        # Upload job description PDF
        console.print(Panel.fit("[bold]Uploading job description PDF...[/bold]", style="cyan"))
        job_desc_file = await project_client.agents.files.upload_and_poll(file_path="job_description.pdf", purpose=FilePurpose.AGENTS)

        # Upload resumes
        console.print(Panel.fit("[bold]Uploading resumes...[/bold]", style="cyan"))
        resume_files = sorted(glob.glob("resumes/*.pdf"))
        resume_file_objs = [
            await project_client.agents.files.upload_and_poll(file_path=f, purpose=FilePurpose.AGENTS)
            for f in resume_files
        ]
        resume_file_ids = [f.id for f in resume_file_objs]
        console.print("[green]Resumes uploaded successfully.[/green]")

        # Create vector store for resumes
        console.print(Panel.fit("[bold]Creating vector store for resumes...[/bold]", style="cyan"))
        resumes_vector_store = await project_client.agents.vector_stores.create_and_poll(
            file_ids=resume_file_ids,
            name="resumes_vector_store"
        )
        console.print(f"[green]Created vector store[/green] (ID: [bold]{resumes_vector_store.id}[/bold])")

        # Create vector store for job description
        console.print(Panel.fit("[bold]Creating vector store for job description...[/bold]", style="cyan"))
        jd_vector_store = await project_client.agents.vector_stores.create_and_poll(
            file_ids=[job_desc_file.id],
            name="job_description_vector_store"
        )
        console.print(f"[green]Created vector store[/green] (ID: [bold]{jd_vector_store.id}[/bold])")

        # Create workflow agent (job summary, access to job description vector store)
        jd_file_search_tool = FileSearchTool(vector_store_ids=[jd_vector_store.id])
        workflow_agent_def = await project_client.agents.create_agent(
            model=deployment_name,
            name="JobPosting_agent",
            instructions=JOB_POSTING_AGENT_INSTRUCTIONS,
            tools=jd_file_search_tool.definitions,
            tool_resources=ToolResources(file_search={"vector_store_ids": [jd_vector_store.id]})
        )

        # Create screening agent (access to resumes vector store)
        screening_file_search_tool = FileSearchTool(vector_store_ids=[resumes_vector_store.id])
        screening_agent_def = await project_client.agents.create_agent(
            model=deployment_name,
            name="CandidateScreening_agent",
            instructions=SCREENING_AGENT_INSTRUCTIONS,
            tools=screening_file_search_tool.definitions,
            tool_resources=ToolResources(file_search={"vector_store_ids": [resumes_vector_store.id]})
        )

        # Create recruiter agent (has workflow agent and screening agent as tools)
        workflow_tool = ConnectedAgentTool(id=workflow_agent_def.id, name="JobPosting_agent", description="Summarizes the job posting.")
        screening_tool = ConnectedAgentTool(id=screening_agent_def.id, name="CandidateScreening_agent", description="Screens a candidate's CV against a job description.")
        recruiter_agent_def = await project_client.agents.create_agent(
            model=deployment_name,
            name="recruiter",
            instructions=RECRUITER_AGENT_INSTRUCTIONS,
            temperature=0.1,
            tools=[screening_tool.definitions[0], workflow_tool.definitions[0]],
        )

        # Create critic agent (no tools)
        critic_agent_def = await project_client.agents.create_agent(
            model=deployment_name,
            name="workflow",
            temperature=0.1,
            instructions=CRITIC_AGENT_INSTRUCTIONS,
        )

        # Create AzureAIAgent objects for group chat
        critic_agent = AzureAIAgent(
            client=project_client,
            definition=critic_agent_def,
            description="Asks questions to identify the best candidates for the job posting."
        )
        recruiter_agent = AzureAIAgent(
            client=project_client,
            definition=recruiter_agent_def,
            description="Recruiter agent with access to candidate data."
        )

        # Define agent response callback
        def agent_response_callback(message: ChatMessageContent) -> None:
            console.print(
                Panel.fit(
                    str(message.content),
                    title=f"{message.name or message.role}",
                    style="bright_blue" if message.name == "TalentAcquisitionSpecialist_agent" else "magenta"
                )
            )

        # Set up group chat orchestration
        agents = [recruiter_agent, critic_agent]
        group_chat_orchestration = GroupChatOrchestration(
            members=agents,
            manager=CustomGroupChatManager(max_rounds=10),
            agent_response_callback=agent_response_callback,
        )

        # Start the runtime
        runtime = InProcessRuntime()
        runtime.start()

        # Initial task/message
        kickoff_message = (
            "Please provide a summary of the job posting. (using myfiles_browser)"
        )

        # Run the orchestration
        console.print(Panel.fit("[bold yellow]\n--- Starting Group Chat ---\n[/bold yellow]", style="magenta"))
        orchestration_result = await group_chat_orchestration.invoke(
            task=kickoff_message,
            runtime=runtime,
        )

        value = await orchestration_result.get()
        console.print(Panel.fit(f"[bold green]--- Group Chat Completed ---[/bold green]\n{value}", style="green"))

        # Optional: Stop the runtime
        await runtime.stop_when_idle()


if __name__ == "__main__":
    asyncio.run(main())