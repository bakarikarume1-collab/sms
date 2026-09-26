# KarumeSMS API Integration

## Start the backend

Run the API and worker in separate terminals:

```powershell
.\virual\Scripts\python.exe app.py
.\virual\Scripts\python.exe sms_worker.py
```

The API is available at `http://127.0.0.1:5001`.

## Queue an SMS

Send a `POST` request to `/notifications/sms`:

```http
POST /notifications/sms
Content-Type: application/json
Idempotency-Key: order-123-confirmation
```

```json
{
  "phone": "0743771438",
  "message": "Habari, oda yako imepokelewa."
}
```

The phone number is normalized to the Tanzania international format (`255...`).
The response is `202 Accepted` while the worker sends the message in the background.

Use the same `Idempotency-Key` when retrying a request. It returns the original SMS instead of creating a duplicate.

## Check SMS status

```http
GET /notifications/sms/{sms_id}
```

Possible statuses include `PENDING`, `PROCESSING`, `RETRY`, `SENT`, and `PERMANENTLY_FAILED`.

## Health check

```http
GET /health
```

Use this endpoint to check whether the backend is running.

## Website origins

Set the website origins in `.env`:

```env
FRONTEND_ORIGINS=http://localhost:3000,http://localhost:5173
WORKER_CLAIM_TIMEOUT_SECONDS=600
```

For production, replace the localhost origins with the real website origin. Keep SMS credentials in the backend `.env`; do not put them in browser code.

## Bulk SMS API

Set `SMS_ADMIN_TOKEN` in the backend `.env` and send it as `X-Admin-Token`.
Campaign creation does not send SMS. Sending requires an explicit request to the
campaign send endpoint.

```http
POST /api/contact-groups
POST /api/contacts
POST /api/contacts/import
POST /api/campaigns
GET /api/campaigns
POST /api/campaigns/{id}/send
GET /api/dashboard/sms
```

Create a campaign with `name`, `message`, and either `contact_ids` or `group_id`.
The SMS segment count uses one segment up to 160 characters and 153-character
segments for longer messages.

The Sakura delivery endpoint is:

```http
POST /api/webhooks/sakura
X-Webhook-Secret: <configured webhook secret>
```

Webhook events are deduplicated by event key. Provider-specific payload fields
are accepted through `event_id`, `message_id` or `id`, and `status`.

## Security configuration

Use `SMS_SERVICE_TOKEN` for requests from KarumeStore to the queue endpoint.
Use a separate `SMS_ADMIN_TOKEN` for bulk administration and
`SMS_WEBHOOK_SECRET` for provider callbacks. Never put these values in browser
JavaScript or commit `.env` files.
