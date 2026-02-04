"""CLI tool for managing the ElevenLabs Voice Agents.

Commands:
    # Buyer Brief Agent
    buyer-agent deploy              Deploy buyer brief agent
    buyer-agent update              Update existing buyer brief agent

    # Sales Associate Agent
    buyer-agent deploy-sales        Deploy sales associate agent

    # Phone & Twilio
    buyer-agent twilio-setup        Import Twilio phone number
    buyer-agent list-numbers        List registered phone numbers

    # Outbound Calls
    buyer-agent call                Single outbound call
    buyer-agent campaign            Run outbound campaign from CSV

    # Conversations
    buyer-agent list-calls          List recent conversations
    buyer-agent get-call            Get conversation details

    # Utilities
    buyer-agent voices              List available voices
    buyer-agent show-config         Show agent configuration
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config.settings import get_settings
from .api_client import ElevenLabsClient
from .agent_config import build_agent_config
from .sales_agent_config import build_sales_agent_config
from .lead_manager import LeadManager, Lead, create_sample_csv

app = typer.Typer(
    name="buyer-agent",
    help="Manage ElevenLabs Voice Agents for Buyer Agency",
)
console = Console()


# ------------------------------------------------------------------
# Buyer Brief Agent Commands
# ------------------------------------------------------------------

@app.command()
def deploy(
    update_id: Optional[str] = typer.Option(
        None,
        "--update",
        "-u",
        help="Update existing agent by ID instead of creating new",
    ),
    voice_id: Optional[str] = typer.Option(
        None,
        "--voice",
        "-v",
        help="Override voice ID",
    ),
    llm_model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override LLM model (e.g., claude-3-5-sonnet)",
    ),
):
    """Deploy the Buyer Brief agent to ElevenLabs.

    This agent conducts phone interviews to gather comprehensive buyer briefs.
    It asks about investment vs owner-occupier status first, then relevant questions.
    """
    settings = get_settings()

    if not settings.elevenlabs_api_key:
        console.print("[red]Error:[/red] ELEVENLABS_API_KEY not set")
        raise typer.Exit(1)

    # Apply overrides
    if voice_id:
        settings.elevenlabs_voice_id = voice_id
    if llm_model:
        settings.elevenlabs_llm_model = llm_model

    async def _deploy():
        async with ElevenLabsClient(settings) as client:
            config = build_agent_config(settings)
            console.print("[blue]Building Buyer Brief agent configuration...[/blue]")

            if update_id:
                console.print(f"[yellow]Updating agent {update_id}...[/yellow]")
                result = await client.update_agent(update_id, config)
                agent_id = update_id
            else:
                console.print("[green]Creating new Buyer Brief agent...[/green]")
                result = await client.create_agent(config)
                agent_id = result.get("agent_id")

            console.print(Panel(
                f"[green]Buyer Brief Agent deployed![/green]\n\n"
                f"Agent ID: [bold]{agent_id}[/bold]\n"
                f"Name: Buyer Brief Agent\n"
                f"LLM: {settings.elevenlabs_llm_model}\n"
                f"Voice: {settings.elevenlabs_voice_id or 'default'}\n\n"
                f"[dim]This agent interviews prospects to build buyer briefs.[/dim]",
                title="Buyer Brief Agent Deployed",
            ))

            return agent_id

    agent_id = asyncio.run(_deploy())
    return agent_id


@app.command("deploy-sales")
def deploy_sales(
    update_id: Optional[str] = typer.Option(
        None,
        "--update",
        "-u",
        help="Update existing sales agent by ID",
    ),
    voice_id: Optional[str] = typer.Option(
        None,
        "--voice",
        "-v",
        help="Override voice ID for sales agent",
    ),
):
    """Deploy the Sales Associate agent to ElevenLabs.

    This agent makes follow-up calls to leads who have shown interest in properties.
    It's designed for outbound campaigns from CSV, CRM, or interest feeds.
    """
    settings = get_settings()

    if not settings.elevenlabs_api_key:
        console.print("[red]Error:[/red] ELEVENLABS_API_KEY not set")
        raise typer.Exit(1)

    if voice_id:
        settings.sales_voice_id = voice_id

    async def _deploy():
        async with ElevenLabsClient(settings) as client:
            config = build_sales_agent_config(settings)
            console.print("[blue]Building Sales Associate agent configuration...[/blue]")

            if update_id:
                console.print(f"[yellow]Updating sales agent {update_id}...[/yellow]")
                result = await client.update_agent(update_id, config)
                agent_id = update_id
            else:
                console.print("[green]Creating new Sales Associate agent...[/green]")
                result = await client.create_agent(config)
                agent_id = result.get("agent_id")

            console.print(Panel(
                f"[green]Sales Associate Agent deployed![/green]\n\n"
                f"Agent ID: [bold]{agent_id}[/bold]\n"
                f"Name: Sales Associate Agent\n"
                f"LLM: {settings.sales_llm_model or settings.elevenlabs_llm_model}\n"
                f"Voice: {settings.sales_voice_id or settings.elevenlabs_voice_id or 'default'}\n\n"
                f"[dim]This agent follows up with leads from property enquiries.[/dim]\n"
                f"[dim]Use 'buyer-agent campaign' to run outbound calls.[/dim]",
                title="Sales Associate Agent Deployed",
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
# Twilio / Phone Number Commands
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
    Inbound calls to this number will be handled by the specified agent.
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
                f"Number ID: {result.get('phone_number_id', 'N/A')}\n\n"
                f"[bold]Inbound calls[/bold] to this number will be handled by agent {agent_id}.\n"
                f"[bold]Outbound calls[/bold] can use this number with 'buyer-agent call'.",
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
# Outbound Call Commands
# ------------------------------------------------------------------

@app.command()
def call(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    to_number: str = typer.Argument(..., help="Phone number to call (e.g., +61400000000)"),
    from_number_id: str = typer.Argument(..., help="Phone number ID to call from"),
    prospect_name: str = typer.Option("", "--name", "-n", help="Prospect name"),
    property_address: str = typer.Option("", "--property", "-p", help="Property address (for sales follow-up)"),
    interest_source: str = typer.Option("", "--source", "-s", help="Interest source (e.g., 'Open Home')"),
):
    """Initiate a single outbound call to a prospect.

    Use this for one-off calls. For bulk outbound, use 'buyer-agent campaign'.
    """
    settings = get_settings()

    async def _call():
        async with ElevenLabsClient(settings) as client:
            console.print(f"[blue]Calling {to_number}...[/blue]")

            variables = {
                "agency_name": settings.agency_name,
            }
            if prospect_name:
                variables["prospect_name"] = prospect_name
            if property_address:
                variables["property_address"] = property_address
            if interest_source:
                variables["interest_source"] = interest_source

            result = await client.initiate_outbound_call(
                agent_id=agent_id,
                to_number=to_number,
                from_number_id=from_number_id,
                custom_variables=variables,
            )

            console.print(Panel(
                f"[green]Call initiated![/green]\n\n"
                f"Call ID: {result.get('call_id', 'N/A')}\n"
                f"To: {to_number}\n"
                f"Status: {result.get('status', 'initiated')}",
                title="Outbound Call",
            ))

    asyncio.run(_call())


@app.command()
def campaign(
    agent_id: str = typer.Argument(..., help="Agent ID (use Sales Associate for follow-ups)"),
    csv_file: Path = typer.Argument(..., help="CSV file with leads"),
    from_number_id: str = typer.Argument(..., help="Phone number ID to call from"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview without calling"),
    delay: int = typer.Option(30, "--delay", help="Seconds between calls"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output results CSV"),
):
    """Run an outbound calling campaign from a CSV file.

    CSV format: name, phone, email, property_address, interest_source, enquiry_date, notes

    Example:
        buyer-agent campaign agent_xxx leads.csv number_yyy --delay 60
    """
    settings = get_settings()

    if not csv_file.exists():
        console.print(f"[red]Error:[/red] CSV file not found: {csv_file}")
        raise typer.Exit(1)

    # Load leads
    manager = LeadManager(settings)
    loaded = manager.load_from_csv(csv_file)
    console.print(f"[green]Loaded {loaded} leads from {csv_file}[/green]")

    leads = manager.get_pending_leads()
    console.print(f"[blue]{len(leads)} leads ready to call[/blue]")

    if dry_run:
        table = Table(title="Campaign Preview (Dry Run)")
        table.add_column("Name", style="green")
        table.add_column("Phone", style="cyan")
        table.add_column("Property")
        table.add_column("Source")
        table.add_column("Days Since")

        for lead in leads[:20]:
            table.add_row(
                lead.name,
                lead.phone,
                lead.property_address[:30] + "..." if len(lead.property_address) > 30 else lead.property_address,
                lead.interest_source,
                str(lead.days_since_enquiry) if lead.enquiry_date else "-",
            )

        console.print(table)
        if len(leads) > 20:
            console.print(f"[dim]... and {len(leads) - 20} more[/dim]")
        console.print("\n[yellow]Dry run - no calls made. Remove --dry-run to execute.[/yellow]")
        return

    # Run campaign
    async def _campaign():
        async with ElevenLabsClient(settings) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Calling {len(leads)} leads...", total=len(leads))

                for i, lead in enumerate(leads):
                    try:
                        progress.update(task, description=f"Calling {lead.name} ({i+1}/{len(leads)})...")

                        variables = lead.to_dynamic_variables()
                        variables["agency_name"] = settings.agency_name

                        result = await client.initiate_outbound_call(
                            agent_id=agent_id,
                            to_number=lead.phone,
                            from_number_id=from_number_id,
                            custom_variables=variables,
                        )

                        lead.status = "called"
                        console.print(f"[green]✓[/green] Called {lead.name}: {result.get('call_id', 'OK')}")

                    except Exception as e:
                        lead.status = "failed"
                        console.print(f"[red]✗[/red] Failed {lead.name}: {e}")

                    progress.advance(task)

                    # Delay between calls
                    if i < len(leads) - 1:
                        await asyncio.sleep(delay)

        # Export results
        if output:
            manager.export_results(output)
            console.print(f"\n[green]Results exported to {output}[/green]")

    asyncio.run(_campaign())

    # Summary
    called = sum(1 for l in leads if l.status == "called")
    failed = sum(1 for l in leads if l.status == "failed")
    console.print(Panel(
        f"Campaign complete!\n\n"
        f"Total: {len(leads)}\n"
        f"[green]Called: {called}[/green]\n"
        f"[red]Failed: {failed}[/red]",
        title="Campaign Summary",
    ))


@app.command("create-sample-csv")
def create_sample(
    output: Path = typer.Argument(Path("sample_leads.csv"), help="Output file path"),
):
    """Create a sample CSV file for lead imports."""
    create_sample_csv(output)
    console.print(f"[green]Sample CSV created: {output}[/green]")
    console.print("[dim]Edit this file with your leads, then use 'buyer-agent campaign'.[/dim]")


# ------------------------------------------------------------------
# Conversation Commands
# ------------------------------------------------------------------

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
# Utility Commands
# ------------------------------------------------------------------

@app.command()
def voices(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search by name or accent"),
):
    """List available voices for the agents."""
    settings = get_settings()

    async def _list():
        async with ElevenLabsClient(settings) as client:
            voice_list = await client.list_voices()

            # Filter if search provided
            if search:
                search_lower = search.lower()
                voice_list = [
                    v for v in voice_list
                    if search_lower in v.get("name", "").lower()
                    or search_lower in str(v.get("labels", {})).lower()
                ]

            table = Table(title="Available Voices")
            table.add_column("Voice ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Category")
            table.add_column("Accent/Labels")

            for voice in voice_list[:30]:
                labels = voice.get("labels", {})
                accent = labels.get("accent", "")
                label_str = accent or ", ".join(f"{k}:{v}" for k, v in labels.items())

                table.add_row(
                    voice.get("voice_id", ""),
                    voice.get("name", ""),
                    voice.get("category", ""),
                    label_str[:40] + "..." if len(label_str) > 40 else label_str,
                )

            console.print(table)

            if len(voice_list) > 30:
                console.print(f"\n[dim]Showing 30 of {len(voice_list)} voices.[/dim]")

            console.print("\n[dim]Tip: Use --search to filter (e.g., --search australian)[/dim]")

    asyncio.run(_list())


@app.command()
def show_config(
    agent_type: str = typer.Option("buyer", "--type", "-t", help="Agent type: buyer or sales"),
):
    """Show the current agent configuration (for debugging)."""
    settings = get_settings()

    if agent_type == "sales":
        config = build_sales_agent_config(settings)
        title = "Sales Associate Configuration"
    else:
        config = build_agent_config(settings)
        title = "Buyer Brief Configuration"

    console.print(Panel(
        json.dumps(config, indent=2, default=str),
        title=title,
    ))


if __name__ == "__main__":
    app()
