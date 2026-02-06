"""
Web Dashboard for ElevenLabs Outbound Calling
Upload prospects, monitor campaigns, view results
"""

import os
import csv
import json
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from outbound_caller import initiate_call, get_call_results

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory storage (use database in production)
campaigns = {}
prospects_db = []
call_logs = []


@app.route('/')
def dashboard():
    """Main dashboard view"""
    return render_template('dashboard.html',
                         prospects=prospects_db,
                         campaigns=campaigns,
                         call_logs=call_logs[-20:])  # Last 20 calls


@app.route('/upload', methods=['POST'])
def upload_prospects():
    """Handle CSV file upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Parse CSV
        new_prospects = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prospect = {
                    'id': len(prospects_db) + len(new_prospects) + 1,
                    'name': row.get('name', ''),
                    'phone': row.get('phone', ''),
                    'email': row.get('email', ''),
                    'context': row.get('context', ''),
                    'status': 'pending',
                    'uploaded_at': datetime.now().isoformat()
                }
                new_prospects.append(prospect)

        prospects_db.extend(new_prospects)

        return jsonify({
            'success': True,
            'message': f'Uploaded {len(new_prospects)} prospects',
            'count': len(new_prospects)
        })

    return jsonify({'error': 'Invalid file type. Please upload a CSV file.'}), 400


@app.route('/prospects', methods=['GET'])
def get_prospects():
    """Get all prospects"""
    return jsonify(prospects_db)


@app.route('/prospects/add', methods=['POST'])
def add_prospect():
    """Add a single prospect"""
    data = request.json
    prospect = {
        'id': len(prospects_db) + 1,
        'name': data.get('name', ''),
        'phone': data.get('phone', ''),
        'email': data.get('email', ''),
        'context': data.get('context', ''),
        'status': 'pending',
        'uploaded_at': datetime.now().isoformat()
    }
    prospects_db.append(prospect)
    return jsonify({'success': True, 'prospect': prospect})


@app.route('/prospects/<int:prospect_id>', methods=['DELETE'])
def delete_prospect(prospect_id):
    """Delete a prospect"""
    global prospects_db
    prospects_db = [p for p in prospects_db if p['id'] != prospect_id]
    return jsonify({'success': True})


@app.route('/campaign/start', methods=['POST'])
def start_campaign():
    """Start calling campaign"""
    data = request.json
    delay = data.get('delay', 60)
    prospect_ids = data.get('prospect_ids', [])

    # Get prospects to call
    if prospect_ids:
        to_call = [p for p in prospects_db if p['id'] in prospect_ids and p['status'] == 'pending']
    else:
        to_call = [p for p in prospects_db if p['status'] == 'pending']

    if not to_call:
        return jsonify({'error': 'No pending prospects to call'}), 400

    campaign_id = f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    campaigns[campaign_id] = {
        'id': campaign_id,
        'status': 'running',
        'total': len(to_call),
        'completed': 0,
        'successful': 0,
        'failed': 0,
        'started_at': datetime.now().isoformat()
    }

    # Run campaign in background thread
    def run_campaign_async():
        import time
        for prospect in to_call:
            if campaigns[campaign_id]['status'] != 'running':
                break

            prospect['status'] = 'calling'
            result = initiate_call(prospect)

            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'prospect_name': prospect['name'],
                'phone': prospect['phone'],
                'success': result['success'],
                'conversation_id': result.get('conversation_id'),
                'error': result.get('error')
            }
            call_logs.append(log_entry)

            if result['success']:
                prospect['status'] = 'called'
                prospect['conversation_id'] = result.get('conversation_id')
                campaigns[campaign_id]['successful'] += 1
            else:
                prospect['status'] = 'failed'
                prospect['error'] = result.get('error')
                campaigns[campaign_id]['failed'] += 1

            campaigns[campaign_id]['completed'] += 1
            time.sleep(delay)

        campaigns[campaign_id]['status'] = 'completed'
        campaigns[campaign_id]['completed_at'] = datetime.now().isoformat()

    thread = threading.Thread(target=run_campaign_async)
    thread.start()

    return jsonify({
        'success': True,
        'campaign_id': campaign_id,
        'prospects_count': len(to_call)
    })


@app.route('/campaign/<campaign_id>/stop', methods=['POST'])
def stop_campaign(campaign_id):
    """Stop a running campaign"""
    if campaign_id in campaigns:
        campaigns[campaign_id]['status'] = 'stopped'
        return jsonify({'success': True})
    return jsonify({'error': 'Campaign not found'}), 404


@app.route('/campaign/<campaign_id>/status', methods=['GET'])
def campaign_status(campaign_id):
    """Get campaign status"""
    if campaign_id in campaigns:
        return jsonify(campaigns[campaign_id])
    return jsonify({'error': 'Campaign not found'}), 404


@app.route('/logs', methods=['GET'])
def get_logs():
    """Get call logs"""
    return jsonify(call_logs[-50:])  # Last 50 logs


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
