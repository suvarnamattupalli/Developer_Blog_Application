from flask import Flask,redirect,url_for,request,render_template,flash,session
import mysql.connector
from flask_session import Session
from key import secret_key,salt
from itsdangerous import URLSafeTimedSerializer
from stoken import token
from cmail import sendmail
from werkzeug.utils import secure_filename
import os
app = Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] ='uploads'
mydb=mysql.connector.connect(host="localhost",user="root",password="admin",db="blog_db")

@app.route('/')
def index():
    return render_template('title.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('SELECT count(*) from users where username=%s and password=%s',[username,password])
        count=cursor.fetchone()[0]
        if count==1:
            session['user']=username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/homepage')
def home():
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from blogs')
        blog_posts= cursor.fetchall()
        cursor.close()
        return render_template('homepage.html', blog_posts=blog_posts)
    else:
        return redirect(url_for('login'))
@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()[0]
        cursor.execute('select count(*) from users where email=%s',[email])
        count1=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            flash('Username Already In Use')
            return render_template('registration.html')
        elif count1==1:
            flash('Email Already In Use')
            return render_template('registration.html')
        data={'username':username,'password':password,'email':email}
        subject='Email Confirmation'
        body=f"Thanks for signing up\n\nfollow this link for further steps-{url_for('confirm',token=token(data),_external=True)}"
        sendmail(to=email,subject=subject,body=body)
        flash('Confirmation link sent to mail')
        return redirect(url_for('login'))
    return render_template('registration.html')
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=180)
    except Exception as e:
        #print(e)
        return 'Link Expired register again'
    else:
        cursor=mydb.cursor(buffered=True)
        username=data['username']
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.close()
            flash('You are already registerterd!')
            return redirect(url_for('login'))
        else:
            cursor.execute('insert into users (username,password,email) values(%s,%s,%s)',[data['username'],data['password'],data['email']])
            mydb.commit()
            cursor.close()
            flash('Details registered!')
            return redirect(url_for('login'))
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        flash('Successfully logged out')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))
@app.route('/search',methods=['GET','POST'])
def search():
    if request.method == 'POST':
        search_query = request.form['search_query']
        cursor=mydb.cursor(buffered=True)
        cursor.execute("SELECT * FROM blogs WHERE title LIKE %s OR content LIKE %s", (f"%{search_query}%", f"%{search_query}%"))
        blog_posts= cursor.fetchall()
        cursor.close()
        return render_template('search.html', blog_posts=blog_posts, query=search_query)
    
@app.route('/new_blog',methods=['GET','POST'])

def new_blog():
    if session.get('user'):
        if request.method=='POST':
            title=request.form['title']
            content=request.form['content']
            username=session.get('user')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into blogs(title,content,name) values(%s,%s,%s)',[title,content,username])
            mydb.commit()
            cursor.close()
            flash('BLOG added successfully')
            return redirect(url_for('blog_list'))
        return render_template('new_blog.html')
    else:
        return redirect(url_for('login'))
@app.route('/blog_list')
def blog_list():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select id,title,date from blogs where name=%s order by date desc',[username])
        data=cursor.fetchall()
        print(data)
        cursor.close()
        return render_template('table.html',data=data)
    else:
        return redirect(url_for('login'))
@app.route('/view_blog/<int:id>')
def view_blog(id):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select title,content from blogs where id=%s',[id])
        data=cursor.fetchone()
        cursor.close()
        title=data[0]
        content=data[1]
        return render_template('view_blog.html',title=title,content=content)
    else:
        return redirect(url_for('login'))
@app.route('/delete/<id>')
def delete(id):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('delete from blogs where id=%s',[id])
        mydb.commit()
        cursor.close()
        flash('BLOG deleted')
        return redirect(url_for('blog_list'))
    else:
        return redirect(url_for('login'))
@app.route('/update/<id>',methods=['GET','POST'])
def update(id):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select title,content from blogs where id=%s',[id])
        data=cursor.fetchone()
        cursor.close()
        title=data[0]
        content=data[1]
        if request.method=='POST':
            title=request.form['title']
            content=request.form['content']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update blogs set title=%s,content=%s where id=%s',[title,content,id])
            mydb.commit()
            flash('BLOG updated Successfully')
            return redirect(url_for('blog_list'))
           
        return render_template('update.html',title=title,content=content)
    else:
        return redirect(url_for('login'))
    
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/dashboard')
def dashboard():
    if session.get('user'):
        return render_template('dashboard.html')
    else:
        return redirect(url_for('login'))

@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():
    if session.get('user'):
        if request.method == 'POST':
            image = request.files['image']
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                return "Image uploaded successfully."
            return "Invalid image file."
        return render_template('upload_image.html')
    else:
        return redirect(url_for('login'))
    


'''@app.route('/archive/<int:blog_id>')
def archive_blogs(blog_id):
    cursor=mydb.cursor(buffered=True)
    cursor.execute("SELECT * FROM blogs WHERE id = %s", (blog_id,))
    blog= cursor.fetchone()
    cursor.execute("INSERT INTO blogs (title, content, name) VALUES (%s, %s, %s)", (blog[1], blog[2], 'name'))
    mydb.commit()
    cursor.execute("DELETE FROM blogs WHERE id = %s", (blog_id,))
    mydb.commit()
    return redirect(url_for('home'))
@app.route('/archived')
def archived_blogs():
    cursor=mydb.cursor(buffered=True)
    cursor.execute("SELECT * FROM archived_blogs ORDER BY archived_at DESC")
    archived_blogs = cursor.fetchall()
    return render_template('archived.html', blogs=archived_blogs)'''


if __name__ == '__main__':
  app.run(use_reloader=True,debug=True)