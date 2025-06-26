import sqlite3
import json
from datetime import datetime

def init_db():
    conn = sqlite3.connect('formbuilder.db')
    cursor = conn.cursor()
    
    # Forms table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_id INTEGER,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL,
            options TEXT,
            is_required BOOLEAN DEFAULT 0,
            order_index INTEGER,
            skip_logic TEXT,
            FOREIGN KEY (form_id) REFERENCES forms (id)
        )
    ''')
    
    # Responses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_id INTEGER,
            question_id INTEGER,
            response_text TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT,
            FOREIGN KEY (form_id) REFERENCES forms (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('formbuilder.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_all_forms():
    conn = get_db_connection()
    forms = conn.execute('SELECT * FROM forms ORDER BY created_at DESC').fetchall()
    conn.close()
    return forms

def get_form_by_id(form_id):
    conn = get_db_connection()
    form = conn.execute('SELECT * FROM forms WHERE id = ?', (form_id,)).fetchone()
    conn.close()
    return form

def get_questions_by_form_id(form_id):
    conn = get_db_connection()
    questions = conn.execute(
        'SELECT * FROM questions WHERE form_id = ? ORDER BY order_index',
        (form_id,)
    ).fetchall()
    conn.close()
    return questions

def save_form(title, description, questions):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert form
    cursor.execute('INSERT INTO forms (title, description) VALUES (?, ?)', (title, description))
    form_id = cursor.lastrowid
    
    # First pass: Insert all questions to get their IDs
    question_ids = {}
    for i, question in enumerate(questions):
        options = question.get('options', [])
        if not isinstance(options, list):
            options = []
        
        try:
            options_json = json.dumps(options)
        except (TypeError, ValueError) as e:
            print(f"Error serializing options: {e}")
            options_json = '[]'
        
        cursor.execute('''
            INSERT INTO questions (form_id, question_text, question_type, options, is_required, order_index, skip_logic)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            form_id,
            question['text'],
            question['type'],
            options_json,
            question.get('required', False),
            i,
            '{}'
        ))
        question_ids[i] = cursor.lastrowid
    
    # Second pass: Update skip logic with correct question IDs
    for i, question in enumerate(questions):
        skip_logic = question.get('skipLogic', {})
        if skip_logic:
            if not isinstance(skip_logic, dict):
                skip_logic = {}
            if 'condition' not in skip_logic:
                skip_logic = {}
            if 'action' not in skip_logic:
                skip_logic = {}
            if skip_logic.get('action') == 'skip' and 'target' not in skip_logic:
                skip_logic = {}
            
            if skip_logic.get('target'):
                try:
                    target_index = int(skip_logic['target'].split('_')[1]) - 1
                    if target_index >= 0 and target_index < len(questions):
                        skip_logic['target'] = str(question_ids[target_index])
                except (ValueError, TypeError, IndexError) as e:
                    print(f"Error converting skip logic target: {e}")
                    skip_logic['target'] = ''
        
        try:
            skip_logic_json = json.dumps(skip_logic)
        except (TypeError, ValueError) as e:
            print(f"Error serializing skip logic: {e}")
            skip_logic_json = '{}'
        
        cursor.execute('''
            UPDATE questions 
            SET skip_logic = ?
            WHERE id = ?
        ''', (skip_logic_json, question_ids[i]))
    
    conn.commit()
    conn.close()
    return form_id

def save_responses(form_id, responses, session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify form exists
    form = cursor.execute('SELECT id FROM forms WHERE id = ?', (form_id,)).fetchone()
    if not form:
        conn.close()
        return False
    
    # Insert responses
    for question_id, response_text in responses.items():
        try:
            question = cursor.execute(
                'SELECT id FROM questions WHERE id = ? AND form_id = ?',
                (question_id, form_id)
            ).fetchone()
            
            if not question:
                print(f"Warning: Question {question_id} not found or doesn't belong to form {form_id}")
                continue
            
            if isinstance(response_text, list):
                response_text = ', '.join(map(str, response_text))
            else:
                response_text = str(response_text)
            
            cursor.execute('''
                INSERT INTO responses (form_id, question_id, response_text, session_id)
                VALUES (?, ?, ?, ?)
            ''', (form_id, question_id, response_text, session_id))
            
        except Exception as e:
            print(f"Error inserting response for question {question_id}: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    return True

def get_form_responses(form_id):
    conn = get_db_connection()
    responses = conn.execute('''
        SELECT r.*, q.question_text, q.question_type
        FROM responses r
        JOIN questions q ON r.question_id = q.id
        WHERE r.form_id = ?
        ORDER BY r.session_id, q.order_index
    ''', (form_id,)).fetchall()
    conn.close()
    return responses

def delete_form(form_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First verify the form exists
    form = cursor.execute('SELECT id FROM forms WHERE id = ?', (form_id,)).fetchone()
    if not form:
        conn.close()
        return False
    
    # Delete all responses for this form
    cursor.execute('DELETE FROM responses WHERE form_id = ?', (form_id,))
    
    # Delete all questions for this form
    cursor.execute('DELETE FROM questions WHERE form_id = ?', (form_id,))
    
    # Finally delete the form itself
    cursor.execute('DELETE FROM forms WHERE id = ?', (form_id,))
    
    conn.commit()
    conn.close()
    return True 