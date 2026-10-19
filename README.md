# ESR Foods Business Operations Management System

A comprehensive ERP + CRM + Inventory + Billing + Restaurant Management System for seafood distribution business.

## Features

- **Product Management**: Track seafood products with categories, varieties, grades, sizes, and pricing
- **Inventory Management**: Real-time stock tracking, batch management, stock movements, and expiry monitoring
- **Vendor Management**: Manage suppliers with purchase tracking and payment history
- **Purchase Management**: Create and track purchase orders with receiving and inventory updates
- **Restaurant Management**: Manage restaurant customers with credit limits and 15-day billing cycles
- **Customer Management**: Track retail customers and their purchase history
- **Order Management**: Create sales orders with stock deduction and delivery tracking
- **Invoice Management**: Generate invoices with payment tracking and status management
- **Payment Management**: Record receipts from restaurants and payments to vendors
- **Expense Management**: Track business expenses by category
- **Reports**: Generate sales, purchases, inventory, restaurant, profit, and 15-day billing reports
- **Dashboard**: Real-time analytics with charts for sales trends, top products, and inventory distribution
- **User Management**: Role-based access control (Admin, Manager, Staff)
- **Notifications**: System notifications for important events
- **Settings**: Configurable company, invoice, inventory, and system settings

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Authentication**: JWT with password hashing (bcrypt)
- **Charts**: Chart.js
- **PDF Generation**: ReportLab (for invoices and statements)

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone or download the project**

   ```bash
   cd "c:/Users/RAJASHEKAR/OneDrive/Documents/ESF Website"
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**

   On Windows:
   ```bash
   venv\Scripts\activate
   ```


4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Create environment configuration**

   Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```

   Edit `.env` and update the following values:
   ```
   DATABASE_URL=sqlite:///esr_foods.db
   SECRET_KEY=generate-a-unique-random-secret-of-at-least-32-characters
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ESR_ADMIN_USERNAME=admin
   ESR_ADMIN_EMAIL=admin@esrfoods.com
   ESR_ADMIN_PASSWORD=
   ```

6. **Initialize the database with seed data**

   ```bash
   python backend/seed_data.py
   ```

   This will create the database and populate it with:
   - Admin, Manager, and Staff roles
   - A single active Admin account (a one-time strong password is generated and printed if ESR_ADMIN_PASSWORD is empty)
   - 9 seafood product categories
   - Default settings

   Product, vendor, restaurant, customer, purchase, and invoice data must be entered in the application; the seed script does not create sample business records. The SQLite path above is resolved from the project directory even when the app is launched from a different working directory.

   Set `ESR_ADMIN_PASSWORD` in `.env` to choose the bootstrap password, or securely save the one-time generated password printed by the seed script. Manager and Staff accounts are created by an Admin or through registration and require Admin approval.

   Keep `DATABASE_URL` set to `sqlite:///esr_foods.db` unless you intentionally want a different database. Relative SQLite paths resolve from the project directory, not the shell's current directory. If Admin sign-in fails, check that `.env` is present in the project root, verify `ESR_ADMIN_USERNAME`, and rerun the seed command with a strong `ESR_ADMIN_PASSWORD`; it updates that Admin account without clearing business records.

## Running the Application

### Start the Application

```bash
python run.py
```

Or using uvicorn directly:
```bash
uvicorn backend.main:app --reload
```

The application will start on:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs (Swagger UI)

## Usage Guide

### Authentication

1. Open http://localhost:8000/ in your browser
2. Sign in with the bootstrap Admin credentials established during database seeding.
3. You will be redirected to the dashboard

### Role-Based Access

- **Admin**: Full system access, user approvals, and system settings
- **Manager**: Business operations and financial reports; no user or system-security management
- **Staff**: Restricted internal notification access only; no customer, inventory valuation, order, financial, or system-security data

New registrations are assigned Staff access and remain pending until an Admin approves them. Admins can reject, disable, and re-enable accounts from **Users**. Sessions expire after the configured JWT lifetime; set `COOKIE_SECURE=true` when serving over HTTPS and use a unique strong `SECRET_KEY` in production.

### Typical Workflow

1. **Add Vendors**: Go to Vendors → Add Vendor → Enter vendor details
2. **Add Products**: Go to Products → Add Product → Enter product details with pricing
3. **Create Purchase**: Go to Purchases → New Purchase → Select vendor, add items → Save
4. **Receive Purchase**: Go to Purchases → Click "Receive" on a purchase → Stock is automatically updated
5. **Add Restaurants**: Go to Restaurants → Add Restaurant → Enter restaurant details with credit limit
6. **Create Order**: Go to Orders → New Order → Select restaurant, add items → Save
7. **Complete Order**: Go to Orders → Click "Complete" → Stock is automatically deducted
8. **Create Invoice**: Go to Invoices → New Invoice → Select order or create manually → Finalize
9. **Record Payment**: Go to Payments → New Payment → Select invoice, enter amount → Save
10. **View Statement**: Go to Restaurants → Click "Statement" on a restaurant → View 15-day billing summary

### Dashboard Analytics

The dashboard provides real-time insights:
- Today's sales and purchases
- Monthly sales and purchases
- Outstanding receivables and vendor payables
- Total stock value
- Active restaurants count
- Low stock and expiring product alerts
- Sales trend chart (6 months)
- Top products by sales
- Top restaurants by sales
- Outstanding payments by restaurant
- Inventory distribution by category

### Reports

Access various reports from the Reports page:
- **Sales Report**: Filter by date range and restaurant
- **Purchases Report**: Filter by date range and vendor
- **Inventory Report**: Current stock status with low stock alerts
- **Restaurants Report**: Sales, payments, and outstanding for all restaurants
- **15-Day Summary**: Billing period summary with collection rate
- **Profit Report**: Revenue, purchases, expenses, and profit analysis

### Settings

Configure system settings from the Settings page:
- **Company Settings**: Name, address, phone, email, GST number
- **Invoice Settings**: Invoice prefix, billing cycle, tax rate
- **Inventory Settings**: Low stock threshold, expiry warning days
- **System Settings**: Currency

## Project Structure

```
ESF Website/
├── backend/
│   ├── auth/
│   │   ├── __init__.py
│   │   └── security.py          # JWT authentication and password hashing
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # User and Role models
│   │   ├── product.py           # Product and Category models
│   │   ├── vendor.py            # Vendor model
│   │   ├── restaurant.py         # Restaurant and RestaurantNote models
│   │   ├── customer.py           # RetailCustomer model
│   │   ├── purchase.py           # Purchase and PurchaseItem models
│   │   ├── order.py              # SalesOrder and SalesOrderItem models
│   │   ├── invoice.py            # Invoice and InvoiceItem models
│   │   ├── payment.py            # Payment model
│   │   ├── expense.py            # Expense model
│   │   ├── batch.py              # ProductBatch model
│   │   ├── stock_movement.py     # StockMovement model
│   │   ├── notification.py       # Notification model
│   │   ├── audit_log.py          # AuditLog model
│   │   └── setting.py            # Setting model
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── products.py           # Product and category endpoints
│   │   ├── inventory.py          # Inventory management endpoints
│   │   ├── vendors.py            # Vendor management endpoints
│   │   ├── purchases.py          # Purchase management endpoints
│   │   ├── restaurants.py         # Restaurant management endpoints
│   │   ├── customers.py          # Customer management endpoints
│   │   ├── orders.py             # Sales order endpoints
│   │   ├── invoices.py           # Invoice endpoints
│   │   ├── payments.py           # Payment endpoints
│   │   ├── expenses.py           # Expense endpoints
│   │   ├── reports.py            # Report generation endpoints
│   │   ├── dashboard.py          # Dashboard analytics endpoints
│   │   ├── users.py              # User management endpoints
│   │   ├── notifications.py       # Notification endpoints
│   │   └── settings.py           # Settings endpoints
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py               # User and Role schemas
│   │   ├── product.py            # Product and Category schemas
│   │   ├── vendor.py             # Vendor schemas
│   │   ├── restaurant.py          # Restaurant schemas
│   │   ├── customer.py           # Customer schemas
│   │   ├── purchase.py           # Purchase schemas
│   │   ├── order.py              # Order schemas
│   │   ├── invoice.py            # Invoice schemas
│   │   ├── payment.py            # Payment schemas
│   │   ├── expense.py            # Expense schemas
│   │   ├── batch.py              # Batch schemas
│   │   ├── stock_movement.py     # Stock movement schemas
│   │   ├── notification.py        # Notification schemas
│   │   ├── audit_log.py           # Audit log schemas
│   │   ├── setting.py            # Setting schemas
│   │   └── dashboard.py           # Dashboard schemas
│   ├── database.py               # Database configuration
│   ├── main.py                   # FastAPI application
│   └── seed_data.py              # Seed data script
├── frontend/
│   ├── css/
│   │   └── style.css             # Main stylesheet with seafood theme
│   ├── js/
│   │   ├── api.js                # API utility functions
│   │   ├── auth.js               # Authentication functions
│   │   ├── dashboard.js          # Dashboard functionality
│   │   ├── products.js           # Products page functionality
│   │   ├── inventory.js          # Inventory page functionality
│   │   ├── vendors.js            # Vendors page functionality
│   │   ├── purchases.py          # Purchases page functionality
│   │   ├── restaurants.py         # Restaurants page functionality
│   │   ├── customers.js          # Customers page functionality
│   │   ├── orders.js             # Orders page functionality
│   │   ├── invoices.py           # Invoices page functionality
│   │   ├── payments.py           # Payments page functionality
│   │   ├── expenses.py           # Expenses page functionality
│   │   ├── reports.js            # Reports page functionality
│   │   ├── notifications.py       # Notifications page functionality
│   │   ├── users.js              # Users page functionality
│   │   └── settings.js           # Settings page functionality
│   ├── login.html                # Login page
│   ├── dashboard.html            # Dashboard page
│   ├── products.html             # Products page
│   ├── inventory.html            # Inventory page
│   ├── vendors.html              # Vendors page
│   ├── purchases.html            # Purchases page
│   ├── restaurants.html          # Restaurants page
│   ├── customers.html           # Customers page
│   ├── orders.html               # Orders page
│   ├── invoices.html             # Invoices page
│   ├── payments.html             # Payments page
│   ├── expenses.html             # Expenses page
│   ├── reports.html              # Reports page
│   ├── notifications.html         # Notifications page
│   ├── users.html                # Users page
│   └── settings.html             # Settings page
├── database/
│   └── (SQLite database created on first run)
├── static/
│   └── (Static assets for serving)
├── .env.example                 # Environment configuration template
├── requirements.txt             # Python dependencies
├── run.py                      # Application startup script
└── README.md                   # This file
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user
- `GET /api/auth/roles` - Get all roles

### Products
- `GET /api/products/` - List products
- `GET /api/products/{id}` - Get product by ID
- `POST /api/products/` - Create product
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product
- `GET /api/products/categories/` - List categories
- `POST /api/products/categories/` - Create category

### Inventory
- `GET /api/inventory/` - List inventory
- `GET /api/inventory/movements` - List stock movements
- `POST /api/inventory/adjustment` - Create stock adjustment
- `GET /api/inventory/batches` - List batches
- `POST /api/inventory/batches` - Create batch
- `GET /api/inventory/summary` - Get inventory summary

### Vendors
- `GET /api/vendors/` - List vendors
- `GET /api/vendors/{id}` - Get vendor by ID
- `POST /api/vendors/` - Create vendor
- `PUT /api/vendors/{id}` - Update vendor
- `GET /api/vendors/{id}/purchases` - Get vendor purchases
- `GET /api/vendors/{id}/payments` - Get vendor payments
- `GET /api/vendors/{id}/summary` - Get vendor financial summary

### Purchases
- `GET /api/purchases/` - List purchases
- `GET /api/purchases/{id}` - Get purchase by ID
- `POST /api/purchases/` - Create purchase
- `PUT /api/purchases/{id}` - Update purchase
- `POST /api/purchases/{id}/receive` - Receive purchase (update inventory)

### Restaurants
- `GET /api/restaurants/` - List restaurants
- `GET /api/restaurants/{id}` - Get restaurant by ID
- `POST /api/restaurants/` - Create restaurant
- `PUT /api/restaurants/{id}` - Update restaurant
- `DELETE /api/restaurants/{id}` - Delete restaurant
- `GET /api/restaurants/{id}/orders` - Get restaurant orders
- `GET /api/restaurants/{id}/invoices` - Get restaurant invoices
- `GET /api/restaurants/{id}/payments` - Get restaurant payments
- `GET /api/restaurants/{id}/summary` - Get restaurant financial summary
- `POST /api/restaurants/{id}/notes` - Add restaurant note
- `GET /api/restaurants/{id}/notes` - Get restaurant notes
- `GET /api/restaurants/{id}/statement` - Get 15-day statement

### Customers
- `GET /api/customers/` - List customers
- `GET /api/customers/{id}` - Get customer by ID
- `POST /api/customers/` - Create customer
- `PUT /api/customers/{id}` - Update customer
- `GET /api/customers/{id}/orders` - Get customer orders

### Orders
- `GET /api/orders/` - List orders
- `GET /api/orders/{id}` - Get order by ID
- `POST /api/orders/` - Create order
- `PUT /api/orders/{id}` - Update order
- `POST /api/orders/{id}/complete` - Complete order (deduct stock)
- `POST /api/orders/{id}/cancel` - Cancel order (restore stock)

### Invoices
- `GET /api/invoices/` - List invoices
- `GET /api/invoices/{id}` - Get invoice by ID
- `POST /api/invoices/` - Create invoice
- `PUT /api/invoices/{id}` - Update invoice
- `POST /api/invoices/{id}/finalize` - Finalize invoice
- `GET /api/invoices/{id}/payments` - Get invoice payments

### Payments
- `GET /api/payments/` - List payments
- `GET /api/payments/{id}` - Get payment by ID
- `POST /api/payments/` - Create payment
- `GET /api/payments/summary` - Get payments summary

### Expenses
- `GET /api/expenses/` - List expenses
- `GET /api/expenses/{id}` - Get expense by ID
- `POST /api/expenses/` - Create expense
- `PUT /api/expenses/{id}` - Update expense
- `DELETE /api/expenses/{id}` - Delete expense
- `GET /api/expenses/summary` - Get expenses summary

### Reports
- `GET /api/reports/sales` - Sales report
- `GET /api/reports/purchases` - Purchases report
- `GET /api/reports/inventory` - Inventory report
- `GET /api/reports/restaurants` - Restaurants report
- `GET /api/reports/restaurants/15-day-summary` - 15-day summary
- `GET /api/reports/profit` - Profit report

### Dashboard
- `GET /api/dashboard/summary` - Dashboard summary statistics
- `GET /api/dashboard/charts` - Dashboard chart data
- `GET /api/dashboard/15-day-summary` - Current 15-day summary

### Users
- `GET /api/users/` - List users
- `GET /api/users/{id}` - Get user by ID
- `POST /api/users/` - Create user
- `PUT /api/users/{id}/deactivate` - Deactivate user
- `PUT /api/users/{id}/activate` - Activate user

### Notifications
- `GET /api/notifications/` - List notifications
- `POST /api/notifications/` - Create notification
- `PUT /api/notifications/{id}/read` - Mark notification as read
- `PUT /api/notifications/read-all` - Mark all notifications as read
- `GET /api/notifications/unread-count` - Get unread count

### Settings
- `GET /api/settings/` - List all settings
- `GET /api/settings/{key}` - Get setting by key
- `POST /api/settings/` - Create setting
- `PUT /api/settings/{key}` - Update setting

## Database Schema

The application uses SQLite with the following main tables:
- `users` - User accounts with roles
- `roles` - User roles (Admin, Manager, Staff)
- `categories` - Product categories
- `products` - Seafood products with pricing and stock
- `vendors` - Supplier information
- `restaurants` - Restaurant customers with credit limits
- `retail_customers` - Retail customers
- `purchases` - Purchase orders
- `purchase_items` - Purchase order line items
- `sales_orders` - Sales orders
- `sales_order_items` - Sales order line items
- `invoices` - Customer invoices
- `invoice_items` - Invoice line items
- `payments` - Payment transactions
- `expenses` - Business expenses
- `product_batches` - Product batch tracking
- `stock_movements` - Stock movement history
- `notifications` - System notifications
- `audit_logs` - Audit trail
- `settings` - System configuration

## Troubleshooting

### Database Issues

If you encounter database errors:
1. Delete the database file: `database/esr_foods.db`
2. Run the seed script again: `python backend/seed_data.py`

### Port Already in Use

If port 8000 is already in use:
1. Change the port in `run.py`:
   ```python
   uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)
   ```

### CORS Errors

If you encounter CORS errors:
1. Check the `ALLOWED_ORIGINS` in your `.env` file
2. Ensure the frontend URL is included in the allowed origins

## Security Notes

- Change the default `SECRET_KEY` in `.env` before deploying to production
- Use strong passwords for all user accounts
- Enable HTTPS in production
- Regularly update dependencies
- Implement proper backup procedures for the database

## License

This project is proprietary software for ESR Foods.

## Support

For support and issues, contact the development team.
