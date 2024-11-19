from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import logging

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    items = db.relationship('CartItem', backref='cart', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')
# Initialize and Populate Database
def create_products():
    with app.app_context():
        db.create_all()
        if not Product.query.first():
            db.session.add_all([
                Product(name="Cool Shirt", price=19.99, image="https://via.placeholder.com/150", category="Clothing"),
                Product(name="Trendy Shoes", price=49.99, image="https://via.placeholder.com/150", category="Footwear"),
                Product(name="Stylish Hat", price=15.99, image="https://via.placeholder.com/150", category="Accessories"),
                Product(name="Sunglasses", price=10.99, image="https://via.placeholder.com/150", category="Accessories"),
                Product(name="Sports Shoes", price=69.99, image="https://via.placeholder.com/150", category="Footwear"),
                Product(name="Jeans", price=39.99, image="https://via.placeholder.com/150", category="Clothing"),
            ])
            db.session.commit()

# Routes
@app.route('/')
def home():
    products = Product.query.all()
    return render_template('home.html', products=products)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))

    # Retrieve or create a cart
    cart_id = session.get('cart_id')
    if not cart_id:
        new_cart = Cart()
        db.session.add(new_cart)
        db.session.commit()
        session['cart_id'] = new_cart.id
        cart_id = new_cart.id
    else:
        new_cart = db.session.get(Cart, cart_id)

    # Add or update cart item
    cart_item = CartItem.query.filter_by(cart_id=cart_id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(cart_id=cart_id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    return redirect(url_for('cart'))



@app.route('/cart')
def cart():
    cart_id = session.get('cart_id')
    if not cart_id:
        return render_template('cart.html', items=[], total=0)

    cart = db.session.get(Cart, cart_id)
    cart_items = [{
        'product': item.product,
        'quantity': item.quantity,
        'subtotal': item.quantity * item.product.price
    } for item in cart.items]
    total = sum(item['subtotal'] for item in cart_items)

    return render_template('cart.html', items=cart_items, total=total)

@app.route('/remove_from_cart/<int:cart_item_id>')
def remove_from_cart(cart_item_id):
    cart_item = db.session.get(CartItem, cart_item_id)
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
    return redirect(url_for('cart'))


@app.route('/category/<string:category_name>')
def category(category_name):
    products = Product.query.filter_by(category=category_name).all()  # Corrected query
    return render_template('category.html', category_name=category_name, products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = db.session.get(Product, product_id)  # Correct database query
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "image": product.image,
        "category": product.category
    })


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        image = request.form.get('image')
        category = request.form.get('category')

        # Validate inputs
        if not name or not price or not image or not category:
            return "All fields are required!", 400

        # Create and save the new product
        new_product = Product(name=name, price=float(price), image=image, category=category)
        db.session.add(new_product)
        db.session.commit()

        return redirect(url_for('home'))

    return render_template('add_product.html')


import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the SendGrid API key from the environment variable
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# Ensure the API key is loaded correctly
if not SENDGRID_API_KEY:
    raise ValueError("SENDGRID_API_KEY is not set in the environment variables.")


# Set your SendGrid API Key


@app.route('/order', methods=['GET', 'POST'])
def order():
    cart_id = session.get('cart_id')
    if not cart_id:
        return redirect(url_for('cart'))

    cart = db.session.get(Cart, cart_id)
    cart_items = [{
        'name': item.product.name,
        'quantity': item.quantity,
        'price': item.product.price,
        'subtotal': item.quantity * item.product.price
    } for item in cart.items]
    total = sum(item['subtotal'] for item in cart_items)

    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            return "Email is required!", 400

        # Compose the email content
        subject = "Your Order Confirmation"
        message_body = "Thank you for your order!\n\n"
        message_body += "Here are the details of your order:\n"
        for item in cart_items:
            message_body += f"{item['name']} (x{item['quantity']}): ${item['subtotal']:.2f}\n"
        message_body += f"\nTotal: ${total:.2f}"

        # Create and send the email with SendGrid
        message = Mail(
            from_email="alabinjan6@gmail.com",  # Replace with your email
            to_emails=email,
            subject=subject,
            plain_text_content=message_body
        )

        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)
            if response.status_code in [200, 202]:
                return "Order placed successfully! Check your email for details.", 200
            else:
                app.logger.error(f"Failed to send email: {response.status_code} {response.body}")
                return "Failed to send email. Please try again later.", 500
        except Exception as e:
            app.logger.error(f"Error sending email: {e}")
            return "An error occurred while sending the email.", 500

    return render_template('order.html', total=total)



if __name__ == '__main__':
    create_products()
    app.run(debug=True)
