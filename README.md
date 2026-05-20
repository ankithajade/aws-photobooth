# 📸 AWS SBG AI Photo Booth

**Crafted by Ankitha Jade and Sadhana S**
Built for **AWS Student Builder Group, DBIT — Vignanotsava 2k26**

---

## 🌟 Overview

The **AI Photo Booth** is an interactive, event-ready web application built with Streamlit and powered by AWS cloud services. Designed to handle heavy event traffic, the app provides a seamless and futuristic photo booth experience directly from the browser.

### ✨ Features

* **Two Immersive Modes:**
  * **Photobooth:** Capture a single frame, enhanced with real-time AWS Rekognition. The AI analyzes emotions, age, and assigns a unique, fun personality trait and vibe check to the user.
  * **Photostrip:** A classic 4-photo capture sequence with customizable vintage/B&W filters and printable layout templates.
* **Real-time Live Camera:** High-performance, zero-lag WebRTC camera feed natively embedded in the browser.
* **Instant Cloud Delivery:** Seamless integration with **AWS S3**. Photos are uploaded instantly, generating a mobile-responsive QR code for users to scan, view, and download their high-res images on the spot.
* **Futuristic UI/UX:** Built with premium typography (Space Grotesk), neon gradients, glassmorphism, and smooth micro-animations.

---

## 🏗️ Architecture & Technologies

* **Frontend & Backend Framework:** [Streamlit](https://streamlit.io/)
* **Camera Streaming:** [streamlit-webrtc](https://github.com/whitphx/streamlit-webrtc)
* **Image Processing:** OpenCV (`cv2`) and Pillow (`PIL`)
* **Cloud Infrastructure:** Boto3 (AWS Python SDK)
  * **AWS Rekognition:** Facial analysis and emotion detection.
  * **AWS S3:** Object storage and public hosting for instant sharing.
* **QR Generation:** `qrcode`

---

## 🚀 Getting Started

### Prerequisites

You need Python 3.10+ and an AWS account with an S3 bucket and Rekognition access.

### 1. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/your-username/aws-photobooth.git
cd aws-photobooth
pip install -r requirements.txt
```

### 2. AWS Credentials Setup

Configure your AWS credentials on the local machine where the app will run.

```bash
aws configure
```

Ensure the IAM user has permissions for:
* `s3:PutObject` (for your specific bucket)
* `rekognition:DetectFaces`

Update the S3 bucket name in `app.py`:
```python
S3_BUCKET = "your-s3-bucket-name"
```

### 3. Run the Application

Start the Streamlit server:

```bash
streamlit run app.py
```

The app will become available at `http://localhost:8501`.

---

## 🧪 Testing & Optimization

This app has been audited and stress-tested for 100+ users.
* **Zero Backend Video Load:** Camera frames are processed strictly client-side via WebRTC.
* **Heavy Asset Caching:** Streamlit `@st.cache_resource` is used for high-res templates to eliminate loading lag.
* **Collision-Proof Uploads:** S3 filenames use random UUIDs alongside timestamps to ensure massive event traffic never overwrites concurrent captures.

---

## 👥 Authors

- **Ankitha Jade**
- **Sadhana S**

Built with ❤️ for **AWS SBG DBIT**.
