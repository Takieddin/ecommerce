from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_babel import Babel, gettext
from datetime import datetime
from flask_uploads  import UploadSet, configure_uploads, IMAGES
from werkzeug.utils import secure_filename  # Correct import
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOADED_PHOTOS_DEST'] = 'static/images'  # Folder to store uploaded images

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Configure Flask-Reuploaded
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)

app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = './translations'

babel = Babel(app)
LANGUAGES = ['en', 'fr', 'ar']

def get_locale():
    return session.get('lang', 'en')

babel.init_app(app, locale_selector=get_locale)

@app.context_processor
def inject_locale():
    return {'get_locale': get_locale()}

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('admin_panel'))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    images = db.Column(db.Text)  # Store comma-separated image filenames

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    name = db.Column(db.String(100))
    address = db.Column(db.Text)
    phone = db.Column(db.String(15))
    wilaya = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='ordered')

@app.route('/')
def admin_panel():
    products = Product.query.all()
    return render_template('admin.html', products=products)

@app.route('/products/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    
    wilayas = ["Adrar", "Chlef", "Laghouat", "Oum El Bouaghi", "Batna", "Béjaïa", "Biskra", "Béchar", "Blida", "Bouira", "Tamanrasset", "Tébessa", "Tlemcen", "Tiaret", "Tizi Ouzou", "Algiers", "Djelfa", "Jijel", "Sétif", "Saïda", "Skikda", "Sidi Bel Abbès", "Annaba", "Guelma", "Constantine", "Médéa", "Mostaganem", "M'Sila", "Mascara", "Ouargla", "Oran", "El Bayadh", "Illizi", "Bordj Bou Arréridj", "Boumerdès", "El Tarf", "Tindouf", "Tissemsilt", "El Oued", "Khenchela", "Souk Ahras", "Tipaza", "Mila", "Aïn Defla", "Naâma", "Aïn Témouchent", "Ghardaïa", "Relizane", "Timimoun", "Bordj Badji Mokhtar", "Ouled Djellal", "Béni Abbès", "In Salah", "In Guezzam", "Touggourt", "Djanet", "El M'Ghair", "El Menia"]
    wilaya_number = 0
    new_wilayas = []
    for w in wilayas:
        wilaya_number += 1
        new_wilayas.append("-"+str(wilaya_number) + " : " + w)

    return render_template('product.html', product=product, wilayas=new_wilayas)

@app.route('/order/<int:product_id>', methods=['POST'])
def submit_order(product_id):
    name = request.form['name']
    address = request.form['address']
    phone = request.form['phone']
    wilaya = request.form['wilaya']
    quantity = request.form['quantity']

    order = Order(product_id=product_id, name=name, address=address, phone=phone, wilaya=wilaya, quantity=quantity)
    db.session.add(order)
    db.session.commit()

    return render_template('order_confirmation.html')

@app.route('/admin/orders/<int:product_id>', methods=['GET', 'POST'])
def admin_orders(product_id):
    if request.method == 'POST':
        order_id = request.form['order_id']
        action = request.form['action']
        if action == 'update':
            status = request.form['status']
            order = Order.query.get(order_id)
            order.status = status
            db.session.commit()
        elif action == 'delete':
            order = Order.query.get(order_id)
            db.session.delete(order)
            db.session.commit()

    sort_by = request.args.get('sort_by', 'id')
    order = request.args.get('order', 'asc')
    filter_by = request.args.get('filter_by')
    filter_value = request.args.get('filter_value')

    query = Order.query.filter_by(product_id=product_id)

    if filter_by and filter_value:
        query = query.filter(getattr(Order, filter_by).like(f"%{filter_value}%"))

    if order == 'asc':
        query = query.order_by(getattr(Order, sort_by).asc())
    else:
        query = query.order_by(getattr(Order, sort_by).desc())

    orders = query.all()
    return render_template('orders.html', orders=orders, product_id=product_id)

@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image_files = request.files.getlist('images')

        image_filenames = []
        for image in image_files:
            filename = secure_filename(image.filename)
            photos.save(image, name=filename)
            image_filenames.append(filename)

        images = ','.join(image_filenames)

        product = Product(name=name, description=description, price=price, images=images)
        db.session.add(product)
        db.session.commit()

        return redirect(url_for('admin_panel'))

    return render_template('add_product.html')

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    # Delete associated images from the filesystem
    if product.images:
        for image in product.images.split(','):
            image_path = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], image)
            if os.path.exists(image_path):
                os.remove(image_path)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/update_product/<int:product_id>', methods=['GET', 'POST'])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = request.form['price']
        
        # Handle new image uploads
        image_files = request.files.getlist('images')
        if image_files:
            # Delete old images from the filesystem
            if product.images:
                for image in product.images.split(','):
                    image_path = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], image)
                    if os.path.exists(image_path):
                        os.remove(image_path)
            # Save new images
            image_filenames = []
            for image in image_files:
                filename = secure_filename(image.filename)
                photos.save(image, name=filename)
                image_filenames.append(filename)
            product.images = ','.join(image_filenames)
        
        db.session.commit()
        return redirect(url_for('admin_panel'))
    return render_template('update_product.html', product=product)

if __name__ == '__main__':
    app.run(debug=True)
