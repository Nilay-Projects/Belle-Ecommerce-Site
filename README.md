# 🛍️ BELLE – E-Commerce Website

**BELLE** is a modern, full-featured e-commerce web application built using **Django** and **Python**, designed to deliver a seamless shopping experience for users and efficient management tools for administrators.

---

## 🚀 Features

### 🧑‍💻 User-Side Functionalities
- Browse products across multiple categories
- Add items to **cart** and **wishlist**
- Apply **filters** and **sorting** for easy product discovery
- Secure **checkout** and order placement
- **Order tracking** and responsive UI for mobile and desktop users

### 🛠️ Admin-Side Functionalities
- **Inventory management** with CRUD (Create, Read, Update, Delete) operations
- **Product analytics** and order statistics
- Manage categories, customers, and product listings

---

## 🧱 Tech Stack

| Layer | Technology |
|-------|-------------|
| **Backend** | Django (Python) |
| **Frontend** | HTML, CSS, JavaScript, Bootstrap |
| **Database** | MySQL |
| **Version Control** | Git & GitHub |
| **Hosting (optional)** | Django local server / any cloud platform |

---

## 🗂️ Project Structure
Belle-Ecommerce-Site/
├── ecommerce_project/ # Main Django project folder
│ ├── init.py
│ ├── settings.py # Project settings
│ ├── urls.py # Global URL routing
│ ├── asgi.py # ASGI application
│ └── wsgi.py # WSGI application
├── shop/ # Core application for product-related functionalities
│ ├── migrations/ # Database migrations
│ ├── init.py
│ ├── admin.py # Admin interface configurations
│ ├── apps.py # App configuration
│ ├── models.py # Database models
│ ├── tests.py # Unit tests
│ ├── views.py # Views for handling requests
│ ├── urls.py # App-specific URL routing
│ ├── static/ # Static files (CSS, JS, images)
│ │ └── shop/
│ │ ├── css/
│ │ ├── js/
│ │ └── images/
│ └── templates/ # HTML templates
│ └── shop/
│ ├── base.html
│ ├── product_list.html
│ └── product_detail.html
├── media/ # User-uploaded files (e.g., product images)
├── static/ # Global static files
│ ├── css/
│ ├── js/
│ └── images/
├── db.sqlite3 # SQLite database file (consider switching to MySQL for production)
├── manage.py # Django's command-line utility
├── requirements.txt # Project dependencies
└── README.md # Project documentation
