# Demucs Frontend - User Guide

## Access the Application

Open your browser and visit: **http://localhost:8000/app/**

## Features

### 🎯 Registration & Login
- **Register**: Create a new account and get **3 free credits** automatically
- **Login**: Sign in with your email and password
- Sessions persist using JWT tokens (30-day expiry)

### 📊 Dashboard
View your account overview:
- Current credit balance
- Recent transactions (purchases, bonuses, job costs)
- Job history with status tracking
- Download completed separations

### 🎵 Upload Audio
1. Click "Upload Audio" button
2. Select an audio file (MP3, WAV, FLAC, OGG - Max 100MB)
3. Choose separation model:
   - **HTDemucs** - Best quality, 4 stems (vocals, drums, bass, other)
   - **HTDemucs Fine-Tuned** - Faster processing
   - **HTDemucs 6-stem** - 6 stems (includes piano, guitar)
4. Click "Separate Audio" (costs 1 credit)
5. Processing happens in the background
6. Return to dashboard to check status and download when complete

### 💳 Purchase Credits
Choose from three pricing tiers:
- **Starter**: 5 credits for $1.00 ($0.20 per credit)
- **Popular**: 25 credits for $4.00 ($0.16 per credit) ⭐ Best Value
- **Pro**: 100 credits for $15.00 ($0.15 per credit)

**Note**: Square payment integration coming in Phase 2. Currently simulates purchase.

## Job Status Indicators

| Status | Description |
|--------|-------------|
| 🟡 **PENDING** | Job queued, waiting to start |
| 🔵 **PROCESSING** | Audio separation in progress |
| 🟢 **COMPLETED** | Ready to download |
| 🔴 **FAILED** | Processing error occurred |

## Keyboard Shortcuts

- Press **Ctrl+R** to refresh job list
- Press **Esc** to return to dashboard

## Tips

1. **Supported formats**: MP3, WAV, FLAC, OGG, M4A, AAC
2. **File size limit**: 100MB per file
3. **Processing time**: 2-5 minutes depending on song length and model
4. **Download format**: ZIP file containing separated stems
5. **Credit system**: 1 credit = 1 song separation

## Troubleshooting

### Login Issues
- Check email and password
- Clear browser cache and cookies
- Try incognito/private browsing mode

### Upload Fails
- Verify file is under 100MB
- Check file format is supported
- Ensure you have at least 1 credit
- Try refreshing the page

### Download Issues
- Make sure job status is "COMPLETED"
- Check browser pop-up blocker
- Try right-click → "Save link as"

### Balance Not Updating
- Refresh the page (F5)
- Log out and log back in
- Check transaction history

## API Integration

For developers wanting to integrate programmatically:

```javascript
// Authentication
const loginResponse = await fetch('http://localhost:8000/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'user@example.com', password: 'password' })
});
const { access_token } = await loginResponse.json();

// Upload audio
const formData = new FormData();
formData.append('file', audioFile);
formData.append('model', 'htdemucs');

const uploadResponse = await fetch('http://localhost:8000/upload', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${access_token}` },
    body: formData
});
const { job_id } = await uploadResponse.json();

// Check status
const statusResponse = await fetch(`http://localhost:8000/status/${job_id}`, {
    headers: { 'Authorization': `Bearer ${access_token}` }
});
const job = await statusResponse.json();

// Download (when completed)
if (job.status === 'COMPLETED') {
    window.location.href = `http://localhost:8000/download/${job_id}`;
}
```

## Mobile Support

The interface is fully responsive and works on:
- 📱 Phones (iOS, Android)
- 📱 Tablets (iPad, Android tablets)
- 💻 Desktop browsers

## Browser Compatibility

Tested and working on:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Security

- 🔒 JWT token authentication
- 🔒 Password hashing with bcrypt
- 🔒 HTTPS recommended for production
- 🔒 No credit card data stored locally
- 🔒 Square handles all payment processing

## Coming Soon (Phase 2)

- 💳 Real Square payment processing
- 📧 Email notifications when jobs complete
- 🔔 Desktop notifications
- 📊 Advanced analytics dashboard
- 🎨 Theme customization
- 📱 Native mobile app
- 🔗 Share separated tracks
- 💾 Cloud storage integration

## Support

For issues or questions:
1. Check this guide
2. Review the [README_PHASE1.md](../README_PHASE1.md)
3. Check backend logs: `docker compose logs backend`
4. Restart services: `docker compose restart`

## Credits & Attribution

- **Demucs** by Meta Research - AI audio separation model
- **FastAPI** - Backend framework
- **PostgreSQL** - Database
- **Square** - Payment processing (Phase 2)
