
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

app = Flask(__name__)

app.secret_key = 'gizli-anahtar'

# MySQL ayarları
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'emre147a'
app.config['MYSQL_DB'] = 'ogrenci_db'

# Fotoğraf yükleme ayarları
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')  # ✅ Burada olacak
mysql = MySQL(app)



def get_exams():
    cur = mysql.connection.cursor()
    cur.execute("SELECT exam_name, exam_date, exam_end_date, duration, class, is_active, created_at FROM exam")
    exams = cur.fetchall()
    cur.close()
    return exams


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    # MySQL bağlantısı
    return mysql.connection

@app.context_processor
def inject_user_data():
    student_number = session.get('username')
    full_name = session.get('fullname', 'Kullanıcı')
    profile_photo = 'default.jpg'

    if student_number:
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT profile_photo FROM users WHERE student_number = %s", (student_number,))
            row = cur.fetchone()
            cur.close()
            if row and row[0]:
                profile_photo = row[0]
        except Exception as e:
            print(f"Veritabanı hatası: {e}")

    return {
        'full_name': full_name,
        'profile_photo': profile_photo
    }

@app.route('/')
def index():
    return render_template('giris.html')

@app.route('/login', methods=['POST'])
def login():
    student_number = request.form.get('username')
    password = request.form.get('password')

    # Öğrenci sorgusu (users tablosu)
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT student_number, first_name, last_name FROM users WHERE student_number = %s AND password = %s", 
                    (student_number, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['username'] = user[0]
            session['fullname'] = f"{user[1]} {user[2]}"
            flash("Giriş başarılı!", "success")
            return redirect(url_for('anasayfa'))  # Öğrenci dashboard'ına yönlendir
        else:
            flash("Kullanıcı adı veya şifre hatalı.", "error")
            return redirect(url_for('index'))
    except Exception as e:
        flash(f"Veritabanı hatası: {e}", "error")
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Çıkış yapıldı.", "success")
    return redirect(url_for('index'))

@app.route('/anasayfa')
def anasayfa():
    student_number = session.get('username')
    start_time = session.get('start_time', datetime.now().isoformat())

    # Veritabanından son giriş tarihini alalım
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT last_login FROM users WHERE student_number = %s", (student_number,))
        result = cur.fetchone()
        cur.close()

        last_login = result[0] if result else 'Bilgi yok'
    except Exception as e:
        flash(f"Veritabanı hatası: {e}", "error")
        last_login = 'Bilgi yok'

    return render_template('anasayfa.html', start_time=start_time, last_login=last_login)

@app.route('/hesapayar', methods=['GET', 'POST'])
def hesap_ayarlari():
    student_number = session.get('username')
    if not student_number:
        flash("Oturum açılmamış!", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Profil fotoğrafı güncelle
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{student_number}_profile.{ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(file_path)
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "UPDATE users SET profile_photo = %s WHERE student_number = %s",
                        (filename, student_number)
                    )
                    mysql.connection.commit()
                    flash("Profil fotoğrafı güncellendi.", "success")
                except Exception as e:
                    flash(f"Fotoğraf güncellenirken hata: {e}", "error")

        # Kişisel bilgileri güncelle
        first_name = request.form.get('first_name')
        last_name  = request.form.get('last_name')
        email      = request.form.get('email')
        phone      = request.form.get('phone')

        try:
            cur = mysql.connection.cursor()
            cur.execute(""" 
                UPDATE users
                SET first_name = %s, last_name = %s, email = %s, phone = %s
                WHERE student_number = %s
            """, (first_name, last_name, email, phone, student_number))
            mysql.connection.commit()
            session['fullname'] = f"{first_name} {last_name}"
            flash("Bilgiler güncellendi.", "success")
        except Exception as e:
            flash(f"Hata: {e}", "error")

        return redirect(url_for('hesap_ayarlari'))

    # GET: bilgileri yükle
    try:
        cur = mysql.connection.cursor()
        cur.execute(""" 
            SELECT first_name, last_name, email, phone, profile_photo
            FROM users
            WHERE student_number = %s
        """, (student_number,))
        row = cur.fetchone()
        cur.close()

        first_name, last_name, email, phone, profile_photo = row if row else ('', '', '', '', '')
    except Exception as e:
        flash(f"Veritabanı hatası: {e}", "error")
        first_name, last_name, email, phone, profile_photo = ('', '', '', '', '')

    return render_template(
        'hesapayar.html',
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        profile_photo=profile_photo  # ✅ fotoğrafı şablona gönderiyoruz
    )

@app.route('/sifremi_unuttum', methods=['GET', 'POST'])
def sifremi_unuttum():
    return render_template('sifremi_unuttum.html')

@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        teacher_number = request.form.get('teacher_number')
        password = request.form.get('password')

        # Öğretmen sorgusu (teachers tablosu)
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT teacher_number, first_name, last_name, teacher_last_login FROM teachers WHERE teacher_number = %s AND password = %s", 
                        (teacher_number, password))
            teacher = cur.fetchone()
            cur.close()

            if teacher:
                session['teacher_number'] = teacher[0]  # ✅ teacher_number
                session['teacher_fullname'] = f"{teacher[1]} {teacher[2]}"

                # Son giriş tarihini güncelleme
                last_login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "UPDATE teachers SET teacher_last_login = %s WHERE teacher_number = %s",
                        (last_login_time, teacher_number)
                    )
                    mysql.connection.commit()
                except Exception as e:
                    flash(f"Son giriş tarihi güncellenirken hata oluştu: {e}", "error")

                flash("Öğretmen girişi başarılı!", "success")
                return redirect(url_for('e'))  # Öğretmen dashboard'ına yönlendir
            else:
                flash("Kullanıcı adı veya şifre hatalı.", "danger")
                return redirect(url_for('teacher_login'))
        except Exception as e:
            flash(f"Veritabanı hatası: {e}", "error")
            return redirect(url_for('teacher_login'))

    return render_template('giris.html')

@app.route('/e')
def e():
    teacher_number = session.get('teacher_number')
    print(f"Session'dan gelen teacher_number: {teacher_number}")  # DEBUG: Konsola yaz

    if not teacher_number:
        flash("Lütfen önce giriş yapın.", "warning")
        return redirect(url_for('teacher_login'))

    # Öğretmenin son giriş bilgisini almak
    teacher_last_login = 'Bilgi yok'
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT teacher_last_login FROM teachers WHERE teacher_number = %s", (teacher_number,))
        result = cur.fetchone()
        cur.close()
        if result:
            teacher_last_login = result[0]
    except Exception as e:
        flash(f"Son giriş verisi alınırken hata: {e}", "danger")

    # Diğer istatistik verilerini almak
    try:
        cur = mysql.connection.cursor()

        # Toplam sınav sayısı (sadece bu öğretmene ait olanlar)
        cur.execute("SELECT COUNT(*) FROM exam")
        total_exams = cur.fetchone()[0]
        print(f"DEBUG: Öğretmen {teacher_number} için toplam sınav sayısı: {total_exams}")

        # Toplam öğrenci sayısı (tüm sistemdeki)
        cur.execute("SELECT COUNT(DISTINCT student_number) FROM users")
        total_students = cur.fetchone()[0]

        # Tamamlanan sınavlar (result tablosunda teacher_number'a göre)
        cur.execute("SELECT COUNT(*) FROM results WHERE teacher_number = %s", (teacher_number,))
        completed_exams = cur.fetchone()[0]

        # Bekleyen sınavlar (aktif olanlar)
        cur.execute("SELECT COUNT(*) FROM exam WHERE teacher_number = %s AND is_active = 1", (teacher_number,))
        pending_exams = cur.fetchone()[0]

        cur.close()
    except Exception as e:
        flash(f"Veritabanı hatası: {e}", "danger")
        total_exams = total_students = completed_exams = pending_exams = 0

    return render_template(
        'e.html',
        total_exams=total_exams,
        total_students=total_students,
        completed_exams=completed_exams,
        pending_exams=pending_exams,
        teacher_last_login=teacher_last_login
    )

@app.route('/teacher_dashboard', methods=['GET', 'POST'])
def teacher_dashboard():
    return render_template('teacher_dashboard.html')

@app.route('/sinavlarim')
def sinavlarim():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Önce tüm sınavları çek
    cursor.execute("SELECT id, exam_name FROM exam")
    exams = cursor.fetchall()  # Liste [(id, exam_name), ...]

    # Soruları exam_id'ye göre çekip dictionary yap
    exam_questions = {}
    for exam in exams:
        exam_id = exam[0]
        cursor.execute("SELECT * FROM questions WHERE exam_id = %s", (exam_id,))
        questions = cursor.fetchall()
        exam_questions[exam_id] = questions  # Bu şekilde exam_id'ye soruları atıyoruz

    cursor.close()

    return render_template('sinavlarim.html', exams=exams, exam_questions=exam_questions)

@app.route('/sinav/<int:exam_id>/baslat', methods=['GET', 'POST'])
def start_exam(exam_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM exam WHERE id=%s", (exam_id,))
    exam = cursor.fetchone()

    if not exam:
        flash("Sınav bulunamadı.", "danger")
        return redirect(url_for('sinavlarim'))

    cursor.execute("SELECT * FROM questions WHERE exam_id=%s", (exam_id,))
    questions = cursor.fetchall()
    cursor.close()

    if request.method == 'POST':
        # Cevapları işle
        # ...
        flash("Sınav tamamlandı!", "success")
        return redirect(url_for('sinavlarim'))

    return render_template('sinav_baslat.html', exam=exam, questions=questions)

@app.route('/sonuclarim', methods=['GET', 'POST'])
def sonuclarim():
    return render_template('sonuclarim.html')

@app.route('/derslerim', methods=['GET', 'POST'])
def derslerim():
    return render_template('derslerim.html')

# Sinav oluşturma sayfasına yönlendiren route
@app.route('/sinav-olustur', methods=['GET', 'POST'])
def sinav_olustur():
    if request.method == 'POST':
        sinav_adi = request.form['sinavAdi']
        ders = request.form['ders']
        exam_date = request.form['examDate']
        exam_end_date = request.form['examEndDate']
        sure = request.form['sure']
        class_select = request.form['classSelect']

        # Soruları çekelim:
        # Formdaki questions, şöyle gelir:
        # questions[1][text], questions[1][option_a], ...
        # request.form çok boyutlu dict gibi davranmaz, o yüzden:
        # request.form.to_dict(flat=False) kullanabiliriz

        from collections import defaultdict
        sorular = defaultdict(dict)

        for key, value in request.form.items():
            # key örn: questions[1][text]
            import re
            m = re.match(r'questions\[(\d+)\]\[(\w+)\]', key)
            if m:
                idx = m.group(1)
                field = m.group(2)
                sorular[idx][field] = value

        try:
            cur = mysql.connection.cursor()
            # Önce sınavı ekle
            cur.execute("""
                INSERT INTO exam (exam_name, exam_date, exam_end_date, duration, class, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (sinav_adi, exam_date, exam_end_date, sure, class_select, 1))
            mysql.connection.commit()

            # Yeni sınav id'sini al
            sinav_id = cur.lastrowid

            # Soruları ekle
            for idx, soru in sorular.items():
                cur.execute("""
                    INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    sinav_id,
                    soru.get('text', ''),
                    soru.get('option_a', ''),
                    soru.get('option_b', ''),
                    soru.get('option_c', ''),
                    soru.get('option_d', ''),
                    soru.get('correct_option', '')
                ))
            mysql.connection.commit()

            flash('Sınav ve sorular başarıyla kaydedildi!', 'success')
            return redirect(url_for('sinavlarim'))

        except Exception as e:
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(url_for('sinav_olustur'))

    return render_template('sinav-olustur.html')

@app.route('/sinav-ekle', methods=['GET', 'POST'])
def sinav_ekle():
    if request.method == 'POST':
        teacher_number = request.form['teacher_number']
        exam_name = request.form['exam_name']
        exam_date = request.form['exam_date']
        duration = request.form['duration']
        total_questions = request.form['total_questions']
        is_active = request.form['is_active']

        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO exam (teacher_number, exam_name, exam_date, duration, total_questions, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (teacher_number, exam_name, exam_date, duration, total_questions, is_active))
            mysql.connection.commit()
            flash("Sınav başarıyla eklendi!", "success")
            return redirect(url_for('sinavlarim'))
        except Exception as e:
            flash(f"Sınav eklenirken hata oluştu: {e}", "error")
            return redirect(url_for('sinav_olustur'))

    return render_template('sinav_olustur.html')

@app.route('/duyurular')
def duyurular():
    return render_template('duyurular.html')  # templates/duyurular.html olmalı

@app.route('/ogrenci-listesi')
def ogrenci_listesi():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT student_number, username, email FROM users")
        students = cur.fetchall()  # liste döner [(student_number, first_name, last_name, email), ...]
        cur.close()
    except Exception as e:
        flash(f"Veritabanı hatası: {e}", "danger")
        students = []

    return render_template('ogrenci-listesi.html', students=students)

@app.route('/cikis')
def cikis():
    session.clear()
    flash("Çıkış yapıldı.", "success")
    return redirect(url_for('index'))

@app.route('/ogrenci-ekle', methods=['GET', 'POST'])
def ogrenci_ekle():
    if request.method == 'POST':
        student_number = request.form.get('student_number')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO users (student_number, username, email, password) VALUES (%s, %s, %s, %s)",
                (student_number, username, email, password)
            )
            mysql.connection.commit()
            flash('Öğrenci başarıyla eklendi!', 'success')
        except Exception as e:
            flash(f'Hata oluştu: {e}', 'danger')
        return redirect(url_for('ogrenci_listesi'))

    # GET isteğinde öğrenci ekleme formunu göster
    return render_template('ogrenci-ekle.html')

@app.route('/ogrenci-sil/<student_number>', methods=['POST'])
def ogrenci_sil(student_number):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM users WHERE student_number = %s", (student_number,))
        mysql.connection.commit()
        flash(f"{student_number} numaralı öğrenci silindi.", "success")
    except Exception as e:
        flash(f"Hata oluştu: {e}", "danger")
    return redirect(url_for('ogrenci_listesi'))

if __name__ == "__main__":
    app.run(debug=True)