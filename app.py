from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask import Flask, request, jsonify, session, send_file
import numpy as np
import faiss
import openai
import os
from flask import Flask, render_template
from flask import Flask, send_file, request
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = 'your_secret_key'


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  
app.config['MYSQL_PASSWORD'] = 'root'  
app.config['MYSQL_DB'] = 'file_management'  
app.config['MYSQL_PORT'] = 3306
app.config['UPLOAD_FOLDER'] = 'uploads'

mysql = MySQL(app)  



if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/test_db')
def test_db():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT DATABASE();")  
        db_name = cur.fetchone()
        return f"Connected to database: {db_name[0]}"
    except Exception as e:
        return f"Error connecting to database: {str(e)}"


@app.route("/")
def home():
    return render_template("index.html")  

# About Page
@app.route("/about")
def about():
    return render_template("about.html")

# Contact Page
@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')  

    data = request.json
    username = data['username']
    email = data['email']
    password = generate_password_hash(data['password'])

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
    existing_user = cur.fetchone()

    if existing_user:
        return jsonify({'success': False, 'message': 'Username or Email already exists!'}), 400

    cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True, 'message': 'Signup successful! Please login.'}), 201


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html') 

    data = request.json
    user_input = data['user_input']
    password = data['password']

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, password FROM users WHERE username = %s OR email = %s", (user_input, user_input))
    user = cur.fetchone()
    cur.close()

    if user and check_password_hash(user[2], password):
        session['user_id'] = user[0]
        session['username'] = user[1]
        return jsonify({'success': True, 'message': 'Login successful!', 'redirect': '/dashboard'})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials!'}), 401





@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('home'))


faiss_index = faiss.IndexFlatL2(1536)  



def generate_embedding(text):
    try:
        response = openai.Embedding.create(
            input=text,
            model="text-embedding-ada-002"
        )
        print("🔹 OpenAI API Response:", response) 
        return np.array(response['data'][0]['embedding'], dtype=np.float32)
    except Exception as e:
        print("❌ OpenAI Error:", str(e))
        return np.zeros(1536, dtype=np.float32)  


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return jsonify({'message': 'Please log in first!'}), 401

    if 'file' not in request.files:
        print("❌ No file received")
        return jsonify({'message': 'No file selected!'}), 400

    file = request.files['file']
    if file.filename == '':
        print("❌ Empty filename")
        return jsonify({'message': 'No file selected!'}), 400

    filename = secure_filename(file.filename)  
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
       
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        file.save(filepath)  
        print(f"✅ File saved: {filepath}")

        
        try:
            embedding = generate_embedding(filename)
            print("✅ Embedding generated:", embedding.shape)
            faiss_index.add(np.expand_dims(embedding, axis=0))
        except Exception as e:
            print("❌ FAISS Error:", str(e))
            return jsonify({'message': 'Error in FAISS indexing!', 'error': str(e)}), 500

       
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO files (file_name, file_path, upload_date, user_id) VALUES (%s, %s, NOW(), %s)", 
                    (filename, filepath, session['user_id']))
        file_id = cur.lastrowid

        cur.execute("INSERT INTO file_embeddings (file_id, embedding) VALUES (%s, %s)", (file_id, embedding.tobytes()))
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'File uploaded and indexed successfully!'})

    except Exception as e:
        print("❌ Upload Error:", str(e))
        return jsonify({'message': 'Error in file upload!', 'error': str(e)}), 500



@app.route('/search', methods=['GET'])
def search_files():
    query = request.args.get('query', '')

    if not query:
        return jsonify({"files": []})

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.id, f.file_name, f.file_path, u.username 
        FROM files f
        JOIN users u ON f.user_id = u.id
        WHERE f.file_name LIKE %s
    """, (f"%{query}%",))

    files = cur.fetchall()
    cur.close()

    file_list = [{"id": f[0], "name": f[1], "path": f[2], "uploaded_by": f[3]} for f in files]
    
    return jsonify({"files": file_list})


@app.route('/download/<int:file_id>')
def download_file(file_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT file_name, file_path FROM files WHERE id = %s", (file_id,))
    file = cursor.fetchone()
    cursor.close()

    if file:
        file_name = file[0]  
        file_path = os.path.join(os.getcwd(), file[1])  

        if os.path.exists(file_path):
            print(f"📂 Downloading: {file_name} | Path: {file_path}") 
            return send_file(
                file_path, 
                as_attachment=True, 
                download_name=secure_filename(file_name)  
            )
        else:
            print("❌ File Not Found:", file_path)
            return "File Not Found", 404
    else:
        return "Invalid File ID", 400

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('home'))



if __name__ == '__main__':
    app.run(debug=True)
