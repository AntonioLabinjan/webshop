from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
db = SQLAlchemy(app)

# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=False)

# Initialize and Populate Database
def create_products():
    with app.app_context():
        db.create_all()  # Ensure tables are created
        if not Product.query.first():  # Add products only if the table is empty
            db.session.add_all([
                Product(name="Cool Shirt", price=19.99, image="https://via.placeholder.com/150"),
                Product(name="Trendy Shoes", price=49.99, image="https://via.placeholder.com/150"),
                Product(name="Stylish Hat", price=15.99, image="https://via.placeholder.com/150"),
            ])
            db.session.commit()

# Routes
@app.route('/')
def home():
    products = Product.query.all()
    return render_template('home.html', products=products)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(product_id)
    session.modified = True
    return redirect(url_for('home'))

@app.route('/cart')
def cart():
    if 'cart' not in session or not session['cart']:
        return render_template('cart.html', items=[], total=0)
    cart_products = Product.query.filter(Product.id.in_(session['cart'])).all()
    total = sum(product.price for product in cart_products)
    return render_template('cart.html', items=cart_products, total=total)

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    session['cart'].remove(product_id)
    session.modified = True
    return redirect(url_for('cart'))

if __name__ == '__main__':
    create_products()  # Initialize database and products before the app runs
    app.run(debug=True)
