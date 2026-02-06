"""
Google Sheets Integration for ElevenLabs Outbound Calling
Syncs prospects from Google Sheet and updates call results

Setup:
1. Create a Google Cloud Project
2. Enable Google Sheets API
3. Create a Service Account and download credentials.json
4. Share your Google Sheet with the service account email

Install: pip install gspread google-auth
"""

import os
import time
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Dict, Optional
from outbound_caller import initiate_call, get_call_results

# Configuration
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID')
SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'Prospects')

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleSheetsSync:
    def __init__(self, credentials_file: str = CREDENTIALS_FILE):
        """Initialize Google Sheets connection"""
        self.credentials = Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES
        )
        self.client = gspread.authorize(self.credentials)
        self.spreadsheet = None
        self.worksheet = None

    def connect(self, spreadsheet_id: str = SPREADSHEET_ID, sheet_name: str = SHEET_NAME):
        """Connect to a specific spreadsheet and worksheet"""
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.worksheet = self.spreadsheet.worksheet(sheet_name)
        print(f"Connected to: {self.spreadsheet.title} / {sheet_name}")
        return self

    def get_prospects(self, status_filter: Optional[str] = None) -> List[Dict]:
        """
        Fetch prospects from the Google Sheet

        Expected columns: Name, Phone, Email, Context, Status, Call Date, Conversation ID, Notes
        """
        records = self.worksheet.get_all_records()

        prospects = []
        for i, row in enumerate(records, start=2):  # Start at row 2 (after header)
            prospect = {
                'row': i,
                'name': row.get('Name', ''),
                'phone': row.get('Phone', ''),
                'email': row.get('Email', ''),
                'context': row.get('Context', ''),
                'status': row.get('Status', 'pending').lower(),
                'call_date': row.get('Call Date', ''),
                'conversation_id': row.get('Conversation ID', ''),
                'notes': row.get('Notes', '')
            }

            # Filter by status if specified
            if status_filter:
                if prospect['status'] == status_filter.lower():
                    prospects.append(prospect)
            else:
                prospects.append(prospect)

        return prospects

    def update_prospect(self, row: int, status: str, conversation_id: str = '', notes: str = ''):
        """Update a prospect's status in the sheet"""
        # Assuming columns: A=Name, B=Phone, C=Email, D=Context, E=Status, F=Call Date, G=Conversation ID, H=Notes
        call_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update Status (column E)
        self.worksheet.update_cell(row, 5, status)
        # Update Call Date (column F)
        self.worksheet.update_cell(row, 6, call_date)
        # Update Conversation ID (column G)
        if conversation_id:
            self.worksheet.update_cell(row, 7, conversation_id)
        # Update Notes (column H)
        if notes:
            self.worksheet.update_cell(row, 8, notes)

        print(f"Updated row {row}: Status={status}")

    def batch_update_prospects(self, updates: List[Dict]):
        """Batch update multiple prospects"""
        for update in updates:
            self.update_prospect(
                row=update['row'],
                status=update['status'],
                conversation_id=update.get('conversation_id', ''),
                notes=update.get('notes', '')
            )

    def create_template_sheet(self):
        """Create a template sheet with proper headers"""
        headers = ['Name', 'Phone', 'Email', 'Context', 'Status', 'Call Date', 'Conversation ID', 'Notes']

        # Clear and set headers
        self.worksheet.clear()
        self.worksheet.append_row(headers)

        # Add some styling (make header bold)
        self.worksheet.format('A1:H1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })

        print("Template sheet created with headers!")


def run_sheets_campaign(
    spreadsheet_id: str,
    sheet_name: str = 'Prospects',
    delay_between_calls: int = 60,
    credentials_file: str = 'credentials.json'
):
    """
    Run a calling campaign from Google Sheets

    1. Fetches prospects with status 'pending'
    2. Calls each prospect
    3. Updates the sheet with results
    """

    print("\n" + "="*60)
    print("GOOGLE SHEETS CALLING CAMPAIGN")
    print("="*60)

    # Connect to sheet
    sync = GoogleSheetsSync(credentials_file)
    sync.connect(spreadsheet_id, sheet_name)

    # Get pending prospects
    prospects = sync.get_prospects(status_filter='pending')

    if not prospects:
        print("No pending prospects found in the sheet.")
        return

    print(f"Found {len(prospects)} pending prospects")
    print("="*60 + "\n")

    # Call each prospect
    for i, prospect in enumerate(prospects, 1):
        print(f"\n[{i}/{len(prospects)}] Calling {prospect['name']} at {prospect['phone']}...")

        # Update status to 'calling'
        sync.update_prospect(prospect['row'], 'calling')

        # Initiate the call
        result = initiate_call(prospect)

        if result['success']:
            print(f"  ✓ Call initiated - ID: {result.get('conversation_id', 'N/A')}")
            sync.update_prospect(
                row=prospect['row'],
                status='called',
                conversation_id=result.get('conversation_id', ''),
                notes='Call initiated successfully'
            )
        else:
            print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
            sync.update_prospect(
                row=prospect['row'],
                status='failed',
                notes=result.get('error', 'Call failed')
            )

        # Wait before next call
        if i < len(prospects):
            print(f"  Waiting {delay_between_calls}s before next call...")
            time.sleep(delay_between_calls)

    print("\n" + "="*60)
    print("CAMPAIGN COMPLETE")
    print("="*60)


def watch_sheet(
    spreadsheet_id: str,
    sheet_name: str = 'Prospects',
    poll_interval: int = 30,
    delay_between_calls: int = 60,
    credentials_file: str = 'credentials.json'
):
    """
    Continuously watch the sheet for new prospects and call them

    Run this as a background service. It will:
    1. Check for new 'pending' prospects every poll_interval seconds
    2. Call any new prospects it finds
    3. Update the sheet with results
    """

    print("\n" + "="*60)
    print("GOOGLE SHEETS WATCHER")
    print(f"Polling every {poll_interval} seconds...")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")

    sync = GoogleSheetsSync(credentials_file)
    sync.connect(spreadsheet_id, sheet_name)

    while True:
        try:
            # Get pending prospects
            prospects = sync.get_prospects(status_filter='pending')

            if prospects:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Found {len(prospects)} pending prospects")

                for prospect in prospects:
                    print(f"  Calling {prospect['name']}...")

                    sync.update_prospect(prospect['row'], 'calling')
                    result = initiate_call(prospect)

                    if result['success']:
                        sync.update_prospect(
                            prospect['row'],
                            'called',
                            conversation_id=result.get('conversation_id', '')
                        )
                        print(f"    ✓ Success")
                    else:
                        sync.update_prospect(
                            prospect['row'],
                            'failed',
                            notes=result.get('error', '')
                        )
                        print(f"    ✗ Failed")

                    time.sleep(delay_between_calls)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No pending prospects", end='\r')

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\n\nWatcher stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(poll_interval)


# Example usage
if __name__ == "__main__":
    print("""
Google Sheets Sync for Voice Agent Campaigns

Usage:
    1. Set up Google Cloud credentials (see docstring above)
    2. Share your Google Sheet with the service account email
    3. Set environment variables:
       - GOOGLE_CREDENTIALS_FILE=credentials.json
       - GOOGLE_SPREADSHEET_ID=your_spreadsheet_id

Commands:
    # Run a one-time campaign
    python google_sheets_sync.py campaign

    # Watch for new prospects continuously
    python google_sheets_sync.py watch

Sheet format (columns):
    A: Name
    B: Phone
    C: Email
    D: Context
    E: Status (pending/calling/called/failed)
    F: Call Date
    G: Conversation ID
    H: Notes
    """)

    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')

        if not spreadsheet_id:
            print("Error: Set GOOGLE_SPREADSHEET_ID environment variable")
            sys.exit(1)

        if command == 'campaign':
            run_sheets_campaign(spreadsheet_id)
        elif command == 'watch':
            watch_sheet(spreadsheet_id)
        else:
            print(f"Unknown command: {command}")
