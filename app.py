from flask import Flask, render_template, request, redirect, session, url_for 
from utils.openai_utils import generate_product_idea
from utils.image_gen import generate_image 
import sqlite3
import uuid
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
from utils.suno_utils import generate_music
from functools import wraps 


DB_URL_ENV = os.getenv("DATABASE_URL", "sqlite:////data/app.db")

if DB_URL_ENV.startswith("sqlite:///"):
    ACTUAL_DATABASE_PATH = DB_URL_ENV[len("sqlite///"):]
elif DB_URL_ENV.startswith("sqlite://"): # Handles missing slash sometimes
    ACTUAL_DATABASE_PATH = DB_URL_ENV[len("sqlite://"):]
else:
    ACTUAL_DATABASE_PATH = DB_URL_ENV # Assume it's already a valid path

# Ensure the directory for the database exists
db_dir = os.path.dirname(ACTUAL_DATABASE_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)
    print(f"Created database directory: {db_dir}")


def get_full_product_details(session_id):
    """Retrieves all relevant product details for a given session ID."""
    try:
        conn = sqlite3.connect(ACTUAL_DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT name, title, description, price, image_filename, audio_url
        FROM product_ideas
        WHERE session_id = ?
        ORDER BY id DESC LIMIT 1
        ''', (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "name": row[0],
                "title": row[1],
                "description": row[2],
                "price": row[3],
                "image_filename": row[4],
                "audio_url": row[5]
            }
        else:
            return None
    except Exception as e:
        print(f"Error retrieving full product details for session {session_id}: {e}")
        return None
    
def get_product_idea_audio(session_id):

    try:
        conn = sqlite3.connect(ACTUAL_DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT audio_url FROM product_ideas WHERE session_id = ? ORDER BY id DESC LIMIT 1", (session_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"Error retrieving audio URL for session {session_id}: {e}")
        return None

def initialize_database():
 conn = sqlite3.connect(ACTUAL_DATABASE_PATH)
 cursor = conn.cursor()

 # Create the product_ideas table if it doesn't exist
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS product_ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
 name TEXT,
 title TEXT NOT NULL,
 image_filename TEXT,
 audio_url TEXT,
            description TEXT,
            price TEXT
 )
 ''')
 print("Database init")
 conn.commit()
 conn.close()

initialize_database()

def save_product_idea_to_db(session_id, name, product_data):
 """Saves the product idea data to the SQLite database."""
 try:
    conn = sqlite3.connect(ACTUAL_DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO product_ideas (session_id, name, title, description, price)
    VALUES (?, ?, ?, ?, ?)
    ''', (session_id, name, product_data.get('title'), product_data.get('description'), product_data.get('price')))
    conn.commit()
    conn.close()
    print("Product idea saved to database.")
 except Exception as e:
    print(f"Error saving product idea to database: {e}")

def update_product_idea_image(session_id, image_filename):
    conn = sqlite3.connect(ACTUAL_DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE product_ideas SET image_filename = ? WHERE session_id = ?",
            (image_filename, session_id)
        )
        conn.commit()
        print(f"Updated image_filename for session_id: {session_id} with filename: {image_filename}")
    except sqlite3.Error as e:
        print(f"Database error while updating image_filename: {e}")
        conn.rollback() # Rollback changes if an error occurs
    finally:
        conn.close()

def update_product_idea_audio(session_id, audio_url):
    """Updates the audio URL for a product idea in the SQLite database."""
    conn = sqlite3.connect(ACTUAL_DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE product_ideas SET audio_url = ? WHERE session_id = ?",
            (audio_url, session_id)
        )
        conn.commit()
        print(f"Updated audio_url for session_id: {session_id} with URL: {audio_url}")
    except sqlite3.Error as e:
        print(f"Database error while updating audio_url: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_product_idea_for_session(session_id):
 """Retrieves the latest product idea for a given session ID from the database."""
 try:
    conn = sqlite3.connect(ACTUAL_DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT title, description, price
    FROM product_ideas
                WHERE session_id = ?
    ORDER BY id DESC LIMIT 1
    ''', (session_id,))

    row = cursor.fetchone()

    conn.close()

    if row:
        # Return as a dictionary for easier access in the template
        return {
            "title": row[0],
            "description": row[1],
            "price": row[2]
        }
    else:
        return None
 except Exception as e:
    print(f"Error retrieving product idea for session {session_id}: {e}")
    return None

app = Flask(__name__)
app.secret_key = 'very_secret_key'  # Replace with a real secret key in production
ACCESS_CODE = "workshop2025"

def code_verified_required(f):  # Renamed for clarity, logic is the same
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_session_id' not in session:
            # 'user_session_id' is only sext after a correct code entry.
            # If it's not here, they need to go through the code entry process.
            return redirect(url_for('enter_code', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def landing():
 initialize_database() 
 session.clear()
 return render_template('landing.html')


@app.route('/enter_code')
def enter_code():
    return render_template('code_entry.html')

@app.route('/process_code', methods=['POST'])
def process_code():
    code = request.form.get('code')
    name = request.form.get('name') # Get the name from the form
    if code == ACCESS_CODE:
        session['name'] = name # Store the name in the session
        session['user_session_id'] = str(uuid.uuid4()) # Generate and store a unique ID
        session.permanent = True
        # Redirect to the first step
        return redirect(url_for('step1_text'))
    else:
        return render_template('code_entry.html', error="Incorrect code. Please try again.")

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/step1_text', methods=['GET', 'POST'])
@code_verified_required
def step1_text():
    if request.method == 'POST':
        prompt = request.form.get('prompt')
        if prompt:
            # Call the generate_product_idea function from utils.openai_utils
            result = generate_product_idea(prompt)
            session_id = session.get('user_session_id')
            user_name = session.get('name', 'Guest')
            save_product_idea_to_db(session_id, user_name, result) # Save the generated product idea to the database
            session['step1_result'] = result
        return render_template('step1_text.html', result=result)
    else:
        result = session.get('step1_result', None)
        return render_template('step1_text.html', result=result)

@app.route('/step2_image', methods=['GET', 'POST'])
@code_verified_required
def step2_image():
    session_id = session.get('user_session_id')
    product_idea = get_product_idea_for_session(session_id)

    if request.method == 'POST':
        if not product_idea:
            return "Product idea not found for this session. Please complete Step 1.", 400 # Bad Request

        additional_prompt = request.form.get('additional_prompt', '')

        # Construct the final prompt for image generation
        base_prompt = f"Create a realistic image WITHOUT ANY TEXT for a product titled '{product_idea.get('title', '')}' with the description: {product_idea.get('description', '')} BUT WITH NO TEXT, only the title NOT the descirpiton."
        if additional_prompt:
            final_prompt = f"{base_prompt} Additional details: {additional_prompt}"
        else:
            final_prompt = base_prompt

        try:
            print(f"Sending image generation prompt to Gemini: {final_prompt}")
            # Use the provided Gemini API code
            image_data = generate_image(final_prompt)
            update_product_idea_image(session_id, image_data)

        except Exception as e:
            print(f"Error generating image with Gemini: {e}")
            # You might want to set an error message in the session or pass it to the template

        if image_data:
            # We will not store the base64 image data in the session to avoid large cookie size.
            # Redirect to GET to display the image and the form again
            return redirect(url_for('step2_image'))
        else:
            # If image generation failed, render the template with an error message
            # Keep the product_idea so the user can see the context
            return render_template('step2_image.html', product_idea=product_idea, error="Image generation failed. Please try again.")


    else: # GET request
        image_data = session.get('step2_image_filename', None) # Retrieve filename from session
        return render_template('step2_image.html', product_idea=product_idea, image_data=image_data)


@app.route('/step3_music', methods=['GET', 'POST'])
@code_verified_required
def step3_music():
    session_id = session.get('user_session_id')
    product_idea = get_product_idea_for_session(session_id)
    image_data = session.get('step2_image_filename', None)
    suno_task_id = session.get('suno_task_id', None) # Retrieve suno_task_id from session

    if request.method == 'POST':
        # If a task ID already exists, don't generate again, just redirect
        if suno_task_id:
            print(f"Task {suno_task_id} already in progress for session {session_id}. Redirecting.")
            return redirect(url_for('step3_music'))

        audio_prompt = request.form.get('audio_prompt')
        
        if not audio_prompt:
            return render_template('step3_music.html', product_idea=product_idea, image_data=image_data, suno_task_id=suno_task_id, error="Music prompt is required.")

        music_data = generate_music(audio_prompt, session_id=session_id)
    

        task_id = None
        if music_data and music_data.get('code') == 200 and music_data.get('data'):
            print("in music_data")
            task_id = music_data['data'].get('taskId')
            if task_id:
                session['suno_task_id'] = task_id # Store the task ID in the session
                print(f"Suno Task ID: {task_id}")
            else:
                print("Music generation request successful, but task ID not found in response.")
                print(music_data) # Print the full response for debugging
        else:
            print("Music generation request failed or response format unexpected.")
            # TODO: Handle the error, maybe pass an error message to the template


    audio_path = session.get('audio_path', None)
    return render_template('step3_music.html', product_idea=product_idea, image_data=image_data, audio_path=get_product_idea_audio(session_id), suno_task_id=session.get('suno_task_id')) # Retrieve audio from DB and pass task_id

@app.route('/suno_callback', methods=['POST'])
def suno_callback():
    # This route will receive the callback from the Suno API
    session_id = request.args.get('session_id')
    
    print("Callback in progress")
    if not session_id:
        print("Callback received without session_id")
        return "Missing session_id", 400

    callback_data = request.json
    if callback_data and callback_data.get('code') == 200 and callback_data.get('data') and callback_data['data'].get('data'):
        audio_url = callback_data['data']['data'][0].get('audio_url')
        if audio_url:
            update_product_idea_audio(session_id, audio_url)
            session['suno_task_id']= None
            print(f"Received callback for session {session_id}, audio URL: {audio_url}")
            return redirect(url_for('step3_music'))
            return "Callback received and processed", 200
    return "Callback received but data format unexpected", 400
@app.route('/step4_video', methods=['GET', 'POST'])
@code_verified_required
def step4_video():
    if request.method == 'POST':
        # Retrieve image path and music path from the session
        image_path = session.get('step2_image_url', '')
        music_path = session.get('step3_music_path', '')
        # Call the placeholder function (assume it returns the video path)
        video_path = video_gen.create_product_video(image_path, music_path)
        session['step4_video_path'] = video_path
        return render_template('step4_video.html', video_path=video_path)
    else:
        video_path = session.get('step4_video_path', None)
        return render_template('step4_video.html', video_path=video_path)
    
@app.route('/showcase') # This is the final result page
@code_verified_required
def showcase_product():
    session_id = session.get('user_session_id')
    if not session_id:
        return redirect(url_for('enter_code'))

    product_details = get_full_product_details(session_id)
    # Use session-specific task ID key
    suno_task_id_in_session = session.get(f'suno_task_id_{session_id}', None)


    if not product_details: # If no product at all (e.g. user jumped to /showcase)
        return redirect(url_for('step1_text'))

    image_url_for_template = None
    if product_details.get('image_filename'):
        image_url_for_template = url_for('static', filename='generated_images/' + product_details['image_filename'])

    # If audio_url is now in DB, the task is complete, ensure session task_id is cleared.
    if product_details.get('audio_url') and suno_task_id_in_session:
        session.pop(f'suno_task_id_{session_id}', None)
        suno_task_id_in_session = None # Update local variable for immediate use in template

    return render_template('showcase.html',
                           product=product_details, # Contains title, desc, price, audio_url, name
                           image_display_url=image_url_for_template,
                           suno_task_id_active=suno_task_id_in_session, # Pass boolean or task_id
                           user_name=product_details.get('name', 'Our Valued Creator'))


@app.route('/step5_website', methods=['GET', 'POST'])
@code_verified_required
def step5_website():
    if request.method == 'POST':
        # Retrieve all stored data from the session
        title = session.get('step1_result', {}).get('title', '')
        description = session.get('step1_result', {}).get('description', '')
        image_url = session.get('step2_image_url', '')
        music_path = session.get('step3_music_path', '')
        video_path = session.get('step4_video_path', '')

        # Generate static HTML page (Placeholder for actual generation logic)
        generated_page_content = f"<h1>{title}</h1><p>{description}</p><img src='{image_url}'><audio controls src='{music_path}'></audio><video controls src='{video_path}'></video>"
        generated_page_path = 'static/generated_pages/product.html'
        with open(generated_page_path, 'w') as f:
            f.write(generated_page_content)

        session['step5_website_path'] = generated_page_path
        return render_template('step5_website.html', generated_page_path=generated_page_path)
    else:
        generated_page_path = session.get('step5_website_path', None)
        return render_template('step5_website.html', generated_page_path=generated_page_path)

@app.route('/result')
def result():
    # Retrieve all stored data from the session
    step1_result = session.get('step1_result', {})
    image_url = session.get('step2_image_url', None)
    music_path = session.get('step3_music_path', None)
    video_path = session.get('step4_video_path', None)
    generated_page_path = session.get('step5_website_path', None)

    # Render result.html, passing all the data
    return render_template('result.html', step1_result=step1_result, image_url=image_url, music_path=music_path, video_path=video_path, generated_page_path=generated_page_path)

