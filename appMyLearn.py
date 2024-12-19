from urllib.parse import uses_relative
from flask_migrate import Migrate
from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import traceback
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///myLearn.db"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

UPLOAD_FOLDER = 'static/img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Lab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, unique=True)  # Название группы
    description = db.Column(db.Text, nullable=True)  # Описание группы (опционально)

    def __repr__(self):
        return f"<Group {self.title}>"

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)  # ФИО студента
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)  # ID группы

    group = db.relationship('Group', backref=db.backref('students', lazy=True))  # Связь с таблицей Group

class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=False)
    grade = db.Column(db.Integer, nullable=False)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)  # Название
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Дата
    content = db.Column(db.Text, nullable=False)  # Текст новости
    image_path = db.Column(db.String(200))  # Путь к картинке

    def __repr__(self):
        return f"<News {self.title}>"

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Note {self.title}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)  # Имя пользователя
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Дата отзыва
    content = db.Column(db.Text, nullable=False)  # Текст отзыва

    def __repr__(self):
        return f'<Review {self.name}>'


@app.route('/', methods=['GET'])
def index():
    all_news = News.query.order_by(News.date.desc()).all()
    return render_template('index.html', news=all_news)

@app.route('/labs')
def labs():
    posts = Lab.query.all()
    return render_template('labs.html', posts=posts)

@app.route('/notes')
def notes():
    notes = Note.query.all()  # Получаем все заметки из базы данных
    return render_template('notes.html', notes=notes)


@app.route('/marks', methods=['GET'])
def marks():
    # Словарь для хранения данных по группам
    groups = {}

    # Извлекаем всех студентов
    students = Student.query.all()

    # Заполняем словарь данными
    for student in students:
        group_title = student.group.title
        if group_title not in groups:
            groups[group_title] = []

        # Получаем оценки студента
        marks = Mark.query.filter_by(student_id=student.id).all()
        student_labs = []
        for mark in marks:
            lab = Lab.query.get(mark.lab_id)
            student_labs.append((lab.title, mark.grade))

        # Добавляем данные студента в группу
        groups[group_title].append({
            'name': student.full_name,
            'labs': student_labs
        })

    # Рендеринг шаблона с передачей данных
    return render_template('marks.html', groups=groups)

@app.route('/admin_console', methods=['POST', 'GET'])
def admin_console():
    if request.method == 'POST':
        title = request.form['lab-title']
        date = request.form['lab-date']
        text = request.form['lab-content']
        date = datetime.strptime(date, '%Y-%m-%d').date()

        post = Lab(date=date, title=title, text=text)

        try:
            db.session.add(post)
            db.session.commit()
            return redirect('/')
        except Exception as e:
            print(f"Ошибка: {e}")
            return f'При добавлении записи произошла ошибка: {str(e)}'
    else:
        return render_template('admin_console.html')

@app.route('/labs_console')
def labs_console():
    return render_template('labs_console.html')

@app.route('/users_console', methods=['GET','POST'])
def users_console():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Создаем нового пользователя
        new_user = User(username=username, password=password)

        # Сохраняем в базу данных
        db.session.add(new_user)
        db.session.commit()

        return render_template('users_console.html')

    return render_template('users_console.html')

@app.route('/notes_console', methods=['GET', 'POST'])
def notes_console():
    if request.method == 'POST':
        title = request.form['lab-title']
        date = datetime.strptime(request.form['lab-date'], '%Y-%m-%d')
        content = request.form['lab-content']

        # Сохранение заметки в базе данных
        new_note = Note(title=title, date=date, content=content)
        db.session.add(new_note)
        db.session.commit()

        return render_template('notes_console.html')

    return render_template('notes_console.html')

@app.route('/post_console')
def post_console():
    return render_template('post_console.html')


@app.route('/marks_console', methods=['POST', 'GET'])
def marks_console():
    if request.method == 'POST':
        try:
            # Получение данных из формы
            student_id = request.form.get('student_id')
            group_title = request.form.get('group-title')
            labs_ids = request.form.getlist('labs[]')
            grades = request.form.getlist('grades[]')

            # Проверяем корректность данных
            if not student_id or not labs_ids or not grades:
                return "Ошибка: Не все данные указаны", 400

            if len(labs_ids) != len(grades):
                return "Ошибка: Количество лабораторных и оценок не совпадает", 400

            # Сохранение оценок
            for lab_id, grade in zip(labs_ids, grades):
                new_mark = Mark(student_id=student_id, lab_id=lab_id, grade=int(grade))
                db.session.add(new_mark)
            db.session.commit()

            return redirect('/marks_console')
        except Exception as e:
            return f"Ошибка сервера: {str(e)}", 500
    else:
        # Получаем студентов и лабораторные работы
        students = Student.query.all()
        labs = Lab.query.all()
        return render_template('marks_console.html', students=students, labs=labs)


@app.route('/add_group', methods=['POST', 'GET'])
def add_group():
    if request.method == 'POST':
        group_title = request.form.get('group-title')
        group_description = request.form.get('group-description', '')

        # Проверка на наличие названия группы
        if not group_title:
            return "Ошибка: название группы обязательно!", 400

        # Создаем новую запись в таблице Group
        try:
            new_group = Group(title=group_title, description=group_description)
            db.session.add(new_group)
            db.session.commit()
            return redirect('/add_group')  # Перенаправляем на ту же страницу после добавления
        except Exception as e:
            return f"Ошибка при добавлении группы: {str(e)}", 500
    else:
        # Получаем все группы для отображения
        groups = Group.query.all()
        return render_template('add_group.html', groups=groups)


@app.route('/add_student_console', methods=['POST', 'GET'])
def add_student_console():
    if request.method == 'POST':
        # Обработка данных из формы
        try:
            student_names = request.form.getlist('student-names[]')  # ФИО студентов
            group_id = request.form['group-id']  # ID группы

            for name in student_names:
                if name.strip():  # Игнорировать пустые строки
                    new_student = Student(full_name=name.strip(), group_id=group_id)
                    db.session.add(new_student)
            db.session.commit()
            return redirect('/add_student_console')
        except Exception as e:
            return f"Ошибка при добавлении студентов: {str(e)}"
    else:
        # Получение списка групп для выбора
        groups = Group.query.all()
        return render_template('add_student_console.html', groups=groups)

@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files['image']

        # Проверка и загрузка картинки
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"{UPLOAD_FOLDER}/{filename}"
        else:
            image_path = None  # Если картинка не загружена

        # Добавление новости в базу данных
        new_news = News(title=title, content=content, image_path=image_path)
        db.session.add(new_news)
        db.session.commit()

        return render_template('add_news.html')

    return render_template('add_news.html')


@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if request.method == 'POST':
        # Получаем данные из формы
        name = request.form['name']
        content = request.form['content']

        # Создаем новый отзыв и сохраняем его в БД
        new_review = Review(name=name, content=content)
        db.session.add(new_review)
        db.session.commit()

        # Перенаправляем пользователя обратно на страницу отзывов
        return render_template('reviews.html')

    # Получаем все отзывы из базы данных
    all_reviews = Review.query.order_by(Review.date.desc()).all()

    # Передаем отзывы в шаблон
    return render_template('reviews.html', all_reviews=all_reviews)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
