"""CLI tool for managing the ElevenLabs Buyer Agent.

Commands:
    buyer-agent deploy          Create or update the agent
    buyer-agent twilio-setup    Import Twilio phone number
    buyer-agent call            Initiate an outbound call
    buyer-agent list-calls      List recent conversations
    buyer-agent test            Run a simulation test
    buyer-agent voices          List available voices
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config.settings import get_settings
from .api_client import ElevenLabsClient
from .agent_config import build_agent_config
from .workflow import build_workflow_config

app = typer.Typer(
    name="buyer-agent",
    help="Manage the ElevenLabs Buyer Brief Voice Agent",
)
console = Console()


# ------------------------------------------------------------------
# Deploy Commands
# ------------------------------------------------------------------

@app.command()
def deploy(
    use_workflow: bool = typer.Option(
        False,
        "--workflow",
        "-w",
        help="Use workflow with subagents instead of single agent",
    ),
    update_id: Optional[str] = typer.Option(
        None,
        "--update",
        "-u",
        help="Update existing agent by ID instead of creating new",
    ),
):
    """Deploy the buyer brief agent to ElevenLabs.

    Creates a new agent or updates an existing one with the current configuration.
    """
    settings = get_settings()

    if not settings.elevenlabs_api_key:
        console.print("[red]Error:[/red] ELEVENLABS_API_KEY not set")
        raise typer.Exit(1)

    async def _deploy():
        async with ElevenLabsClient(settings) as client:
            # Build configuration
            if use_workflow:
                config = build_workflow_config(settings)
                console.print("[blue]Building workflow configuration with subagents...[/blue]")
            else:
                config = build_agent_config(settings)
                console.print("[blue]Building single-agent configuration...[/blue]")

            # Create or update
            if update_id:
                console.print(f"[yellow]Updating agent {update_id}...[/yellow]")
                result = await client.update_agent(update_id, config)
                agent_id = update_id
            else:
                console.print("[green]Creating new agent...[/green]")
                result = await client.create_agent(config)
                agent_id = result.get("agent_id")

            console.print(Panel(
                f"[green]Agent deployed successfully![/green]\n\n"
                f"Agent ID: [bold]{agent_id}[/bold]\n"
                f"Name: {config.get('name', 'Buyer Brief Agent')}\n"
                f"LLM: {settings.elevenlabs_llm_model}\n"
                f"Voice: {settings.elevenlabs_voice_id or 'default'}\n\n"
                f"[dim]Save the Agent ID for future commands.[/dim]",
                title="Deployment Complete",
            ))

            return agent_id

    agent_id = asyncio.run(_deploy())
    return agent_id


@app.command()
def list_agents():
    """List all deployed agents."""
    settings = get_settings()

    async def _list():
        async with ElevenLabsClient(settings) as client:
            agents = await client.list_agents()

            if not agents:
                console.print("[yellow]No agents found.[/yellow]")
                return

            table = Table(title="Deployed Agents")
            table.add_column("Agent ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Status")
            table.add_column("Created")

            for agent in agents:
                table.add_row(
                    agent.get("agent_id", ""),
                    agent.get("name", ""),
                    agent.get("status", ""),
                    agent.get("created_at", "")[:10] if agent.get("created_at") else "",
                )

            console.print(table)

    asyncio.run(_list())


@app.command()
def delete_agent(
    agent_id: str = typer.Argument(..., help="Agent ID to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete an agent."""
    if not confirm:
        confirm = typer.confirm(f"Delete agent {agent_id}?")
        if not confirm:
            raise typer.Abort()

    settings = get_settings()

    async def _delete():
        async with ElevenLabsClient(settings) as client:
            await client.delete_agent(agent_id)
            console.print(f"[green]Agent {agent_id} deleted.[/green]")

    asyncio.run(_delete())


# ------------------------------------------------------------------
# Twilio Commands
# ------------------------------------------------------------------

@app.command("twilio-setup")
def twilio_setup(
    agent_id: str = typer.Argument(..., help="Agent ID to connect"),
    label: str = typer.Option(
        "Buyer Agency Line",
        "--label",
        "-l",
        help="Friendly name for the phone number",
    ),
):
    """Import Twilio phone number and connect to agent.

    The phone number is read from TWILIO_PHONE_NUMBER environment variable.
    """
    settings = get_settings()

    if not settings.has_twilio:
        console.print("[red]Error:[/red] Twilio credentials not configured")
        console.print("Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER")
        raise typer.Exit(1)

    async def _setup():
        async with ElevenLabsClient(settings) as client:
            console.print(f"[blue]Importing {settings.twilio_phone_number}...[/blue]")

            result = await client.import_twilio_number(
                agent_id=agent_id,
                phone_number=settings.twilio_phone_number,
                label=label,
            )

            console.print(Panel(
                f"[green]Phone number imported![/green]\n\n"
                f"Number: {settings.twilio_phone_number}\n"
                f"Label: {label}\n"
                f"Number ID: {result.get('phone_number_id', 'N/A')}\n"
                f"Capabilities: {result.get('capabilities', {})}\n\n"
                f"[dim]Inbound calls to this number will now be handled by the agent.[/dim]",
                title="Twilio Setup Complete",
            ))

    asyncio.run(_setup())


@app.command("list-numbers")
def list_numbers():
    """List registered phone numbers."""
    settings = get_settings()

    async def _list():
        async with ElevenLabsClient(settings) as client:
            numbers = await client.list_phone_numbers()

            if not numbers:
                console.print("[yellow]No phone numbers registered.[/yellow]")
                return

            table = Table(title="Phone Numbers")
            table.add_column("ID", style="cyan")
            table.add_column("Number", style="green")
            table.add_column("Label")
            table.add_column("Agent ID")

            for num in numbers:
                table.add_row(
                    num.get("phone_number_id", ""),
                    num.get("phone_number", ""),
                    num.get("label", ""),
                    num.get("agent_id", ""),
                )

            console.print(table)

    asyncio.run(_list())


# ------------------------------------------------------------------
# Call Commands
# ------------------------------------------------------------------

@app.command()
def call(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    to_number: str = typer.Argument(..., help="Phone number to call (e.g., +61400000000)"),
    from_number_id: str = typer.Argument(..., help="Phone number ID to call from"),
    prospect_name: str = typer.Option("", "--name", "-n", help="Prospect name for greeting"),
):
    """Initiate an outbound call to a prospect."""
    settings = get_settings()

    async def _call():
        async with ElevenLabsClient(settings) as client:
            console.print(f"[blue]Calling {to_number}...[/blue]")

            variables = {}
            if prospect_name:
                variables["prospect_name"] = prospect_name
            variables["agency_name"] = settings.agency_name

            result = await client.initiate_outbound_call(
                agent_id=agent_id,
                to_number=to_number,
                from_number_id=from_number_id,
                custom_variables=variables if variables else None,
            )

            console.print(Panel(
                f"[green]Call initiated![/green]\n\n"
                f"Call ID: {result.get('call_id', 'N/A')}\n"
                f"To: {to_number}\n"
                f"Status: {result.get('status', 'initiated')}",
                title="Outbound Call",
            ))

    asyncio.run(_call())


@app.command("list-calls")
def list_calls(
    agent_id: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
):
    """List recent conversations."""
    settings = get_settings()

    async def _list():
        async with ElevenLabsClient(settings) as client:
            conversations = await client.list_conversations(agent_id=agent_id, limit=limit)

            if not conversations:
                console.print("[yellow]No conversations found.[/yellow]")
                return

            table = Table(title="Recent Conversations")
            table.add_column("ID", style="cyan")
            table.add_column("Started")
            table.add_column("Duration")
            table.add_column("Status")

            for conv in conversations:
                duration = conv.get("duration_seconds", 0)
                duration_str = f"{duration // 60}m {duration % 60}s" if duration else "N/A"

                table.add_row(
                    conv.get("conversation_id", "")[:12] + "...",
                    conv.get("start_time", "")[:16] if conv.get("start_time") else "",
                    duration_str,
                    conv.get("status", ""),
                )

            console.print(table)

    asyncio.run(_list())


@app.command("get-call")
def get_call(
    conversation_id: str = typer.Argument(..., help="Conversation ID"),
    show_transcript: bool = typer.Option(False, "--transcript", "-t", help="Show full transcript"),
):
    """Get details of a specific conversation."""
    settings = get_settings()

    async def _get():
        async with ElevenLabsClient(settings) as client:
            conv = await client.get_conversation(conversation_id)

            console.print(Panel(
                f"Conversation ID: {conv.get('conversation_id')}\n"
                f"Status: {conv.get('status')}\n"
                f"Duration: {conv.get('duration_seconds', 0)} seconds\n"
                f"Start: {conv.get('start_time', 'N/A')}\n"
                f"End: {conv.get('end_time', 'N/A')}\n\n"
                f"Evaluations: {json.dumps(conv.get('analysis', {}).get('evaluations', {}), indent=2)}\n"
                f"Data Collected: {json.dumps(conv.get('analysis', {}).get('data_collection', {}), indent=2)}",
                title="Conversation Details",
            ))

            if show_transcript and conv.get("transcript"):
                console.print("\n[bold]Transcript:[/bold]")
                for turn in conv["transcript"]:
                    role = turn.get("role", "unknown")
                    text = turn.get("text", "")
                    color = "green" if role == "agent" else "blue"
                    console.print(f"[{color}]{role.upper()}:[/{color}] {text}")

    asyncio.run(_get())


# ------------------------------------------------------------------
# Testing Commands
# ------------------------------------------------------------------

@app.command()
def test(
    agent_id: str = typer.Argument(..., help="Agent ID to test"),
    scenario: str = typer.Option(
        "A first-time buyer looking for a 3-bedroom house in Sydney's western suburbs with a budget of $800k",
        "--scenario",
        "-s",
        help="Test scenario description",
    ),
):
    """Run a simulation test against the agent."""
    settings = get_settings()

    async def _test():
        async with ElevenLabsClient(settings) as client:
            console.print(f"[blue]Running simulation...[/blue]")
            console.print(f"Scenario: {scenario}\n")

            result = await client.run_simulation(
                agent_id=agent_id,
                scenario=scenario,
                evaluation_criteria=[
                    "brief_completeness",
                    "customer_satisfaction",
                    "stayed_on_topic",
                ],
            )

            console.print(Panel(
                f"Simulation ID: {result.get('simulation_id')}\n"
                f"Status: {result.get('status')}\n\n"
                f"[bold]Evaluations:[/bold]\n"
                f"{json.dumps(result.get('evaluations', {}), indent=2)}",
                title="Simulation Results",
            ))

    asyncio.run(_test())


# ------------------------------------------------------------------
# Voice Commands
# ------------------------------------------------------------------

@app.command()
def voices():
    """List available voices for the agent."""
    settings = get_settings()

    async def _list():
        async with ElevenLabsClient(settings) as client:
            voice_list = await client.list_voices()

            table = Table(title="Available Voices")
            table.add_column("Voice ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Category")
            table.add_column("Labels")

            for voice in voice_list[:20]:  # Show first 20
                labels = voice.get("labels", {})
                label_str = ", ".join(f"{k}:{v}" for k, v in labels.items())

                table.add_row(
                    voice.get("voice_id", ""),
                    voice.get("name", ""),
                    voice.get("category", ""),
                    label_str[:40] + "..." if len(label_str) > 40 else label_str,
                )

            console.print(table)
            console.print(f"\n[dim]Showing 20 of {len(voice_list)} voices. "
                         f"Set ELEVENLABS_VOICE_ID in .env to use a specific voice.[/dim]")

    asyncio.run(_list())


@app.command()
def show_config():
    """Show the current agent configuration (for debugging)."""
    settings = get_settings()
    config = build_agent_config(settings)

    console.print(Panel(
        json.dumps(config, indent=2, default=str),
        title="Agent Configuration",
    ))


if __name__ == "__main__":
    app()
