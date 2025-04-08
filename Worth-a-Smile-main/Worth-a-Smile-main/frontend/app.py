from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
import cv2
import logging
import base64
import json
import os

app = Flask(__name__)


app.secret_key = 'your_secret_key'

# logging
logging.basicConfig(filename='smile_detection.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')

# JSON file where user points will be stored
USER_POINTS_FILE = 'user_points.json'
JOKES_FILE = 'jokes.json'  # saving user-submitted jokes

# Load user points from JSON file 
def load_user_points():
    if os.path.exists(USER_POINTS_FILE):
        with open(USER_POINTS_FILE, 'r') as file:
            return json.load(file)
    return {}

# Save user points to JSON file
def save_user_points():
    with open(USER_POINTS_FILE, 'w') as file:
        json.dump(user_points, file)

# Load jokes 
def load_jokes():
    if os.path.exists(JOKES_FILE):
        with open(JOKES_FILE, 'r') as file:
            return json.load(file)
    return []  

# Save jokes
def save_jokes(jokes):
    with open(JOKES_FILE, 'w') as file:
        json.dump(jokes, file)

# Initialize points 
user_points = load_user_points()

# Initialize jokes 
jokes = load_jokes()

# Load models for smile detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

# Smile detection 
def detect_smile(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    smile_detected = False
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y+h, x:x+w]
        smiles = smile_cascade.detectMultiScale(roi_gray, scaleFactor=1.8, minNeighbors=20)

        if len(smiles) > 0:
            smile_detected = True
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, 'Smiling - You win 10 points!', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            logging.info("Smile detected! You win 10 points.")
        else:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.putText(frame, 'Not Smiling', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            logging.info("No smile detected.")
    
    return frame, smile_detected

# loads jokes from the file
def get_random_joke():
    if jokes:
        random_joke = random.choice(jokes)
        return random_joke
    else:
        return "No jokes available."

# Route for login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
       
        if username and password:
            session['username'] = username
            if username not in user_points:
                user_points[username] = 0  
                save_user_points()  
            return redirect(url_for('index'))
        else:
            return "Invalid credentials", 401

    return render_template('login.html')

# Route for main page 
@app.route('/')
def index():
    if 'username' in session:
        username = session['username']
        points = user_points.get(username, 0)
        return render_template('index.html', username=username, points=points)
    return redirect(url_for('login'))

@app.route('/get_joke', methods=['GET'])
def joke():
    joke = get_random_joke()
    return jsonify({'joke': joke})

@app.route('/submit_joke', methods=['POST'])
def submit_joke():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 403

    # Get joke on request
    joke = request.json.get('joke')

    # Ensure joke lenght (8 words)
    if len(joke.split()) < 8:
        return jsonify({'error': 'Joke must be at least 8 words long'}), 400

    # Save joke to the list and give points
    jokes.append(joke)
    save_jokes(jokes)  

    username = session['username']
    user_points[username] += 10 
    save_user_points()
    logging.info(f"User {username} submitted a joke and earned 10 points!")
    
    return jsonify({'message': 'Joke submitted successfully!', 'points': user_points[username]}), 200

@app.route('/capture_photo', methods=['POST'])
def capture_photo():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 403
    
    camera = cv2.VideoCapture(0)
    success, frame = camera.read()
    
    if success:
        
        frame, smile_detected = detect_smile(frame)
        
        if smile_detected:
            # If smile is detected, give 10 points to the user
            username = session['username']
            user_points[username] += 10  
            save_user_points()  
            logging.info(f"User {username} smiled! 10 points added.")
        
        # Convert frame to image for show on frontend
        _, img_encoded = cv2.imencode('.jpg', frame)
        img_bytes = img_encoded.tobytes()
        camera.release()

        return jsonify({
            'image': base64.b64encode(img_bytes).decode('utf-8'),
            'smile_detected': smile_detected,
            'points': user_points[session['username']]  
        })
    else:
        return jsonify({'error': 'Failed to capture image'}), 500

# Route for logout 
@app.route('/logout')
def logout():
    session.clear()  
    return redirect(url_for('login'))  

if __name__ == '__main__':
    app.run(debug=True)
