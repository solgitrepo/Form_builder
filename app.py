from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
from datetime import datetime
import database

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

@app.route('/')
def index():
    forms = database.get_all_forms()
    return render_template('index.html', forms=forms)

@app.route('/create_form')
def create_form():
    return render_template('create_form.html')

@app.route('/save_form', methods=['POST'])
def save_form():
    try:
        data = request.json
        title = data.get('title')
        description = data.get('description', '')
        questions = data.get('questions', [])
        
        if not title:
            return jsonify({'success': False, 'error': 'Form title is required'}), 400
        
        print(f"Saving form: {title}")
        print(f"Questions: {questions}")
        
        form_id = database.save_form(title, description, questions)
        return jsonify({'success': True, 'form_id': form_id})
    except Exception as e:
        print(f"Error saving form: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/form/<int:form_id>')
def view_form(form_id):
    form = database.get_form_by_id(form_id)
    questions = database.get_questions_by_form_id(form_id)
    
    if not form:
        flash('Form not found')
        return redirect(url_for('index'))
    
    # Convert questions to dict format for easier handling
    questions_data = []
    for q in questions:
        question_dict = {
            'id': q['id'],
            'text': q['question_text'],
            'type': q['question_type'],
            'options': json.loads(q['options']) if q['options'] else [],
            'required': q['is_required'],
            'skipLogic': json.loads(q['skip_logic']) if q['skip_logic'] else {}
        }
        questions_data.append(question_dict)
    
    return render_template('view_form.html', form=form, questions=questions_data)

@app.route('/submit_response', methods=['POST'])
def submit_response():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
            
        form_id = data.get('form_id')
        responses = data.get('responses', {})
        session_id = data.get('session_id', str(datetime.now().timestamp()))
        
        if not form_id:
            return jsonify({'success': False, 'error': 'Form ID is required'}), 400
            
        if not responses:
            return jsonify({'success': False, 'error': 'No responses provided'}), 400
        
        print(f"Submitting response for form {form_id}")
        print(f"Session ID: {session_id}")
        print(f"Responses: {responses}")
        
        success = database.save_responses(form_id, responses, session_id)
        if not success:
            return jsonify({'success': False, 'error': 'Form not found'}), 404
            
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error in submit_response: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/results/<int:form_id>')
def view_results(form_id):
    form = database.get_form_by_id(form_id)
    responses = database.get_form_responses(form_id)
    
    # Convert form Row to dict
    form_dict = dict(form) if form else None
    
    # Group responses by session and convert Row objects to dicts
    sessions = {}
    for response in responses:
        session_id = response['session_id']
        if session_id not in sessions:
            sessions[session_id] = []
        # Convert Row to dict
        response_dict = dict(response)
        sessions[session_id].append(response_dict)
    
    return render_template('results.html', form=form_dict, sessions=sessions)

@app.route('/delete_form/<int:form_id>', methods=['DELETE'])
def delete_form(form_id):
    try:
        success = database.delete_form(form_id)
        if not success:
            return jsonify({'success': False, 'error': 'Form not found'}), 404
            
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error deleting form: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    database.init_db()
    app.run(debug=True)