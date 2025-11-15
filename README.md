# Belle-Ecommerce-Site

**Belle-Ecommerce-Site** is a modern e-commerce website built with **Django and Python**. The platform allows users to browse and purchase a wide range of products including **men's and women's clothing, shoes, jewelry, cosmetics, and accessories**. This project demonstrates a complete web development workflow, including data management, product listing, templates, static and media files, and admin panel integration.

---

## Project Overview
Belle-Ecommerce-Site provides a seamless shopping experience with:
- Product listing and detailed product pages
- Clean and responsive UI
- Admin panel for managing products
- Support for multiple categories: clothing, shoes, jewelry, cosmetics, and more
- Fully functional backend using Django's MTV architecture
- SQLite database (can be upgraded to MySQL/PostgreSQL)

---

## Features
- Browse products by category
- Product details with images and descriptions
- Admin interface for adding, editing, and deleting products
- Static and media file management
- Ready for deployment and customization

---

## Technologies Used
- **Backend:** Django, Python  
- **Database:** SQLite (default)  
- **Frontend:** HTML, CSS, Bootstrap  
- **Static & Media Files:** Managed in `static/` and `media/` folders  
- **Dependencies:** Listed in `requirements.txt`  

---

## Folder Structure

Belle-Ecommerce-Site/
├── ecommerce_project/      # Main Django project folder
│   ├── settings.py         # Project settings
│   ├── urls.py             # Global URLs
│   ├── asgi.py             
│   └── wsgi.py             
├── shop/                   # Core app for product management
│   ├── admin.py            
│   ├── models.py           
│   ├── views.py            
│   ├── urls.py             
│   ├── templates/shop/     # HTML templates
│   │   ├── base.html
│   │   ├── product_list.html
│   │   └── product_detail.html
│   └── static/shop/        # App static files (CSS, JS, images)
├── media/                  # User-uploaded product images
├── static/                 # Global static files
├── db.sqlite3              # SQLite database
├── manage.py               # Django CLI utility
└── requirements.txt        # Project dependencies

---

## Product Categories
- Men's Clothing  
- Women's Clothing  
- Shoes  
- Jewelry  
- Cosmetics  
- Accessories  

Each category has **product listings** and **detailed pages** for a complete shopping experience.

---

## Future Improvements
- User authentication and registration  
- Shopping cart and checkout system  
- Integration with payment gateways (Stripe/PayPal)  
- Product search and filtering  
- Product reviews and ratings  
- Deployment on cloud (Heroku, AWS)  
- Improved UI with responsive design for mobile devices  

---

## Author
**Your Name**  
- GitHub: [YourGitHub](https://github.com/YourUsername)  
- Email: your.email@example.com  

> Belle-Ecommerce-Site demonstrates full-stack web development skills with Django, Python, and front-end templating. Perfect for showcasing a production-ready e-commerce application for recruiters or portfolio purposes.
