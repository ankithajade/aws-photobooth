# 🎞️ AFTER HOURS 1.0 — Standalone Photostrip Experience

**An Inter-College 24-Hour Technical Hackathon**  
Organized by: **Department of CSE, Don Bosco Institute of Technology (DBIT)** × **AWS Student Builder Group DBIT**  
Powered by: **Unstop** | Co-powered by: **Tridha**  
Event Dates: **30th & 31st October, 2026**

---

## 🌟 Overview

This repository hosts the **Standalone Photostrip Booth** built for the **AFTER HOURS 1.0** hackathon. It replaces the old multi-mode AI Photo Booth with a dedicated, high-performance, standalone 4-photo photostrip experience tailored to the hackathon's brand identity.

### ✨ Features

* **Direct Photostrip Experience:** Opens directly into the 4-photo capture workflow without intermediate navigation, landing pages, or legacy single-booth modes.
* **Official Hackathon Visual Theme:** Styled with the official *AFTER HOURS 1.0* aesthetic (radiant cyber orange, deep dark obsidian tech background, architectural grid, and custom event badges).
* **Live Camera with WebRTC:** Zero-latency, browser-based camera feed (4:3 ratio, selfie-mirrored) with public Google STUN server configuration for cross-network WebRTC reliability.
* **4 Curated Strip Templates:**
  * **After Hours (Official):** Dedicated hackathon frame featuring official event typography and styling.
  * **Retro Event:** Classic multi-slot layout.
  * **Neon Party:** Vibrant event border.
  * **Classic Film:** Analog film-strip layout.
* **Real-time Live Filters:** Instant switching between **Color**, **Black & White**, and **Vintage / Retro** with 0-latency precomputed LUTs.
* **Automated 4-Photo Capture:** Sequential 3-second countdowns per photo with screen flash animation and progress tracking.
* **High-Quality Compositing:** Automatic cover-scaling, center-cropping, and alpha-layering beneath transparent PNG templates at 736 × 1308 resolution.
* **Instant QR Code Sharing:** Automatic S3 upload generating a mobile-responsive companion HTML share page with native Web Share API integration.
* **Local Fallback Download:** Direct PNG download button (`Download Photostrip`) is always available on the booth screen even without AWS credentials or cloud connectivity.

---

## 🏗️ Architecture & Technologies

* **Application Framework:** [Streamlit](https://streamlit.io/)
* **Camera Streaming:** [streamlit-webrtc](https://github.com/whitphx/streamlit-webrtc) with STUN peer connectivity
* **Image Processing:** [OpenCV Headless](https://pypi.org/project/opencv-python-headless/) & [Pillow](https://python-pillow.org/)
* **QR Code Generation:** [qrcode](https://pypi.org/project/qrcode/)
* **Cloud Storage & Delivery:** [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) (AWS S3)

---

## 🚀 Getting Started

### 1. Installation

```bash
git clone -b hackathon-photostrip https://github.com/ankithajade/aws-photobooth.git
cd aws-photobooth
pip install -r requirements.txt
```

### 2. Local Configuration (`secrets.toml`)

Copy the template:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml`:
```toml
AWS_ACCESS_KEY_ID = "YOUR_AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "YOUR_AWS_SECRET_ACCESS_KEY"
AWS_DEFAULT_REGION = "ap-south-1"
S3_BUCKET = "your-s3-bucket-name"

# Set to true only if your bucket has a public read policy configured.
# If false (default), secure 48-hour presigned URLs are used automatically.
S3_USE_PUBLIC_URLS = false

# Optional: Add AWS_SESSION_TOKEN if using temporary STS/Academy credentials
# AWS_SESSION_TOKEN = "YOUR_SESSION_TOKEN"
```

> **Security Note:** `.streamlit/secrets.toml` is ignored by Git and must never be committed.

### 3. Run Application

```bash
streamlit run app.py
```

Access the booth at `http://localhost:8501`.

---

## ☁️ AWS & S3 Configuration Guide

To enable mobile QR code scanning and cloud uploads:

### 1. S3 Bucket Setup
1. Create a bucket in your AWS account (e.g. `afterhours-photostrip-2026`).
2. Region: `ap-south-1` (or your preferred region).
3. **CORS Configuration:** In your S3 bucket permissions, add CORS:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": []
  }
]
```

### 2. IAM Policy Requirements
The IAM user or role executing the application requires only minimal S3 permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::your-s3-bucket-name/*"
    }
  ]
]
```
*(Notice: No Rekognition or administrative IAM permissions are needed!)*

### 3. Private vs Public Buckets
* **Default (Recommended):** The bucket can keep **Block Public Access enabled**. The application generates presigned URLs valid for 48 hours for both the strip image and companion HTML page.
* **Public/CloudFront:** If you host strips behind CloudFront or static website hosting, set `S3_USE_PUBLIC_URLS = true` in secrets.

---

## 🌐 Cloud Deployment (Streamlit Community Cloud / Server)

1. Fork or push the `hackathon-photostrip` branch to GitHub.
2. Link your repo on [Streamlit Community Cloud](https://share.streamlit.io).
3. Set the **Main file path** to `app.py`.
4. Under **Advanced Settings > Secrets**, paste the contents of your `.streamlit/secrets.toml`.
5. Deploy!
   * *Note on Camera:* Browsers require HTTPS to grant camera permissions (`getUserMedia`). Streamlit Community Cloud provides automatic SSL/HTTPS.

---

## 👥 Student Coordinators & Event Leads

- **Madhu T K** — AWS SBG Leader, DBIT
- **Ankitha Jade** — Student Coordinator (+91 6360024049)
- **Sadhana S** — Student Coordinator (+91 9141800861)

Built for **AFTER HOURS 1.0** — Department of CSE, DBIT × AWS Student Builder Group DBIT.
