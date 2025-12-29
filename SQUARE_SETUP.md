# Square Payment Integration Guide

This guide will help you set up Square payments for Mux Minus credit purchases.

## Prerequisites

- A Square account (free to create)
- Access to the Square Developer Dashboard

## Step 1: Create a Square Developer Account

1. Go to [Square Developer Portal](https://developer.squareup.com/)
2. Sign up for a free account or log in
3. Accept the developer terms

## Step 2: Create an Application

1. In the Square Developer Dashboard, go to **Applications**
2. Click **+ Create Your First Application** (or **+ New Application**)
3. Give your application a name (e.g., "Mux Minus")
4. Click **Save**

## Step 3: Get Your Credentials

### For Testing (Sandbox Mode)

1. Click on your application
2. Go to the **Credentials** tab
3. Make sure you're viewing **Sandbox** credentials (toggle at the top)
4. Copy the following:
   - **Sandbox Application ID**
   - **Sandbox Access Token**

### Get Location ID

1. Still in the **Credentials** tab
2. Scroll down to **Sandbox test accounts**
3. Click on **Locations**
4. Copy the **Location ID** for your test location

## Step 4: Configure Mux Minus

1. In your Mux Minus project directory, copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Square credentials:
   ```env
   SQUARE_ENVIRONMENT=sandbox
   SQUARE_ACCESS_TOKEN=EAAAl...your_sandbox_access_token
   SQUARE_APPLICATION_ID=sandbox-sq0idb-...
   SQUARE_LOCATION_ID=L...your_location_id
   ```

3. Restart the containers:
   ```bash
   docker compose down
   docker compose up -d
   ```

## Step 5: Test Payments

1. Go to http://localhost:8000 and log in
2. Click **Buy Credits**
3. Select a package
4. Use Square's test card numbers:

### Test Card Numbers (Sandbox)

#### Successful Payment
- **Card Number**: `4111 1111 1111 1111`
- **CVV**: Any 3 digits
- **Expiration**: Any future date
- **Postal Code**: Any valid postal code

#### Different Card Brands
- **Visa**: `4111 1111 1111 1111`
- **Mastercard**: `5105 1051 0510 5100`
- **Amex**: `3782 822463 10005`
- **Discover**: `6011 0009 9013 9424`

#### Test Decline Scenarios
- **Insufficient Funds**: `4000 0000 0000 0341`
- **Invalid CVV**: `4000 0000 0000 0101`
- **Generic Decline**: `4000 0000 0000 0002`

## Step 6: Go Live (Production)

When you're ready to accept real payments:

1. In Square Developer Dashboard, switch to **Production** credentials
2. Update your `.env` file:
   ```env
   SQUARE_ENVIRONMENT=production
   SQUARE_ACCESS_TOKEN=EAAAl...your_production_access_token
   SQUARE_APPLICATION_ID=sq0idp-...
   SQUARE_LOCATION_ID=L...your_production_location_id
   ```

3. Update `index.html` to use production Square.js:
   - Change: `https://sandbox.web.squarecdn.com/v1/square.js`
   - To: `https://web.squarecdn.com/v1/square.js`

4. Restart containers:
   ```bash
   docker compose down
   docker compose up -d
   ```

## Payment Flow

1. User selects a credit package
2. Square card form appears
3. User enters card details
4. Frontend tokenizes the card (Square.js)
5. Token sent to backend
6. Backend processes payment via Square API
7. On success, credits added to user account
8. Transaction logged in database

## Pricing Structure

| Package | Credits | Price | Per Credit |
|---------|---------|-------|------------|
| Starter | 5       | $1.00 | $0.20      |
| Popular | 25      | $4.00 | $0.16      |
| Pro     | 100     | $15.00| $0.15      |

To change pricing, edit:
- `frontend/index.html` - Display prices
- `frontend/app.js` - Payment amounts

## Security Notes

- ✅ Card details never touch your server (tokenized by Square.js)
- ✅ Square handles PCI compliance
- ✅ Access tokens should be kept secret
- ✅ Use environment variables, never commit `.env` to git
- ✅ Sandbox and Production use separate credentials

## Troubleshooting

### "Payment processing not configured"
- Check that `.env` file exists with Square credentials
- Restart docker containers after adding credentials
- Check backend logs: `docker compose logs backend`

### "Square.js failed to load"
- Check internet connection
- Verify Square.js script is loading in browser console
- Try clearing browser cache

### Payment fails in production but works in sandbox
- Verify you're using **production** credentials
- Check that you've switched the Square.js URL
- Ensure SQUARE_ENVIRONMENT=production in `.env`

### Check Backend Logs
```bash
docker compose logs -f backend
```

Look for:
- "Square client initialized in sandbox mode"
- Payment success/failure messages
- Error details

## Support

- [Square Developer Documentation](https://developer.squareup.com/docs)
- [Square Web Payments SDK](https://developer.squareup.com/docs/web-payments/overview)
- [Square API Reference](https://developer.squareup.com/reference/square)

## Fees

Square charges per transaction:
- **Sandbox**: Free (test mode)
- **Production**: 2.9% + $0.30 per successful transaction

Calculate your net revenue accordingly when setting prices.
