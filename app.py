import os
import sqlite3
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='.', static_folder='.')

# إعداد مجلد لرفع الصور
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # الحد الأقصى لحجم الصورة 16 ميجابايت

# إنشاء قاعدة البيانات والجداول إذا لم تكن موجودة
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # جدول المنتجات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            image TEXT NOT NULL
        )
    ''')
    
    # جدول الآراء والمراجعات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            text TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# مسار لعرض الصفحة الرئيسية
@app.route('/')
def index():
    return render_template('index.html')

# مسار للوصول إلى الصور المرفوعة
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- واجهات برمجية لـ المنتجات (Products API) ---

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    rows = cursor.fetchall()
    conn.close()
    
    products = []
    for row in rows:
        products.append({
            'id': row['id'],
            'name': row['name'],
            'price': row['price'],
            'category': row['category'],
            'image': row['image']
        })
    return jsonify(products)

@app.route('/api/products', methods=['POST'])
def add_product():
    # استقبال البيانات من Form Data للتعامل مع رفع الملفات
    name = request.form.get('name')
    price = request.form.get('price')
    category = request.form.get('category')
    file = request.files.get('image')
    
    if not name or not price or not category or not file:
        return jsonify({'error': 'جميع الحقول مطلوبة بما فيها الصورة'}), 400
    
    # حفظ الصورة بشكل آمن
    filename = secure_filename(file.filename)
    # توليد اسم فريد لتجنب تكرار الأسماء
    unique_filename = f"{os.urandom(8).hex()}_{filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
    
    image_url = f"/uploads/{unique_filename}"
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, price, category, image) VALUES (?, ?, ?, ?)',
                   (name, float(price), category, image_url))
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    
    return jsonify({
        'message': 'تم إضافة المنتج بنجاح!',
        'product': {'id': product_id, 'name': name, 'price': float(price), 'category': category, 'image': image_url}
    })

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # جلب مسار الصورة أولاً لحذفها من السيرفر
    cursor.execute('SELECT image FROM products WHERE id = ?', (product_id,))
    row = cursor.fetchone()
    if row:
        img_path = row[0].lstrip('/')
        if os.path.exists(img_path):
            try:
                os.remove(img_path)
            except:
                pass
                
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'تم حذف المنتج بنجاح'})
    
    conn.close()
    return jsonify({'error': 'المنتج غير موجود'}), 404

# --- واجهات برمجية لـ الآراء (Reviews API) ---

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reviews ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    
    reviews = []
    for row in rows:
        reviews.append({
            'id': row['id'],
            'name': row['name'],
            'rating': int(row['rating']),
            'text': row['text']
        })
    return jsonify(reviews)

@app.route('/api/reviews', methods=['POST'])
def add_review():
    data = request.get_json()
    if not data or 'name' not in data or 'rating' not in data or 'text' not in data:
        return jsonify({'error': 'بيانات التقييم ناقصة'}), 400
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO reviews (name, rating, text) VALUES (?, ?, ?)',
                   (data['name'], int(data['rating']), data['text']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'شكراً لمشاركة رأيك!'})

if __name__ == '__main__':
    app.run(debug=True)