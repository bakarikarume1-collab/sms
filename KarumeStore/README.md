# KarumeStore

Complete Flask + SQLite e-commerce starter.

## Features

- Customer registration/login/logout
- Password hashing
- Customer/admin roles
- Product catalog
- Categories
- Online product image URLs
- Search, category filtering and sorting
- Cart
- Cash on Delivery checkout
- Order lifecycle:
  PENDING -> CONFIRMED -> PROCESSING -> OUT_FOR_DELIVERY -> DELIVERED -> RECEIVED
- Customer order confirmation after delivery
- Notifications
- Admin dashboard APIs
- Admin product/category/order management
- Clean API-first structure for future AI/WhatsApp integration
- Welcome SMS after customer registration

## Windows setup

Open PowerShell inside this folder:

```powershell
python -m venv beka
.\beka\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python app.py
```

Open:

- http://127.0.0.1:5000/
- http://127.0.0.1:5000/products
- http://127.0.0.1:5000/login
- http://127.0.0.1:5000/admin
- http://127.0.0.1:5000/admin/sms

## SMS registration integration

Run the SMS backend and worker from the parent `messages` folder:

```powershell
.\virual\Scripts\python.exe app.py
.\virual\Scripts\python.exe sms_worker.py
```

Then run KarumeStore from this folder:

```powershell
python app.py
```

When a customer registers, the `whatsapp_number` submitted on the form is sent
to the SMS queue as a welcome notification. Set this in KarumeStore `.env`:

```env
SMS_SERVICE_URL=http://127.0.0.1:5001
SMS_SERVICE_TOKEN=the_same_value_as_the_SMS_backend_service_token
SMS_ADMIN_TOKEN=the_same_value_as_the_SMS_backend_admin_token
```

Registration is completed even if the SMS backend is temporarily unavailable;
the response reports `sms_notification.queued` so the website can display the
actual queue result.

The `/admin/sms` page uses a server-side proxy. SMS admin tokens are never sent
to browser JavaScript. Create contacts manually or by CSV, create a campaign,
review its recipient and segment count, and press **Send Campaign** explicitly.

## Default local admin

Email:

`admin@karumestore.local`

Password:

`Admin@12345`

Change these before using the project outside local development.

## API examples

GET `/api/products`

GET `/api/categories`

POST `/api/auth/register`

POST `/api/auth/login`

GET `/api/auth/me`

GET `/api/cart`

POST `/api/cart/items`

POST `/api/orders`

GET `/api/orders`

POST `/api/orders/<id>/received`

GET `/api/admin/dashboard`

PUT `/api/admin/orders/<id>/status`

## Future AI integration

The order system is already separated around APIs and notifications, so later an AI/WhatsApp service can consume events such as:

- NEW_ORDER_CREATED
- ORDER_STATUS_CHANGED
- ORDER_RECEIVED

Do not expose the Flask secret key, admin password, or database publicly.
