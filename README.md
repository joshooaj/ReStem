<p align="center">
  <img src="app/static/images/logo-horizontal.svg" alt="Mux Minus" width="400">
</p>

<h3 align="center">
  🎵 Separate Your Music Into Individual Tracks
</h3>

<p align="center">
  Break down any song into individual stems for vocals, drums, bass, guitar, piano, and more.
  <br />
  Powered by <a href="https://github.com/facebookresearch/demucs">Demucs</a> from Facebook Research.
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#ai-models">AI Models</a> •
  <a href="#screenshots">Screenshots</a> •
  <a href="#about-demucs">About Demucs</a> •
  <a href="#tech-stack">Tech Stack</a>
</p>

---

## ✨ Features

| | |
|---|---|
| 🎯 **High Quality** | Powered by Demucs, an open-source AI model from Facebook Research |
| ⚡ **Fast Processing** | No need to install anything — just upload your files |
| 🎨 **Multiple Stem Options** | Choose from 2, 4, or 6 stem separation |
| 🔒 **Privacy First** | Files automatically deleted after 24 hours |
| 💰 **Pay As You Go** | No subscriptions — start with 3 free credits |
| 🌐 **API Access** | Integrate stem separation into your workflow *(coming soon)* |

---

## 🚀 How It Works

<table>
<tr>
<td align="center" width="33%">

### 1️⃣ Upload

Upload any audio file — MP3, WAV, FLAC, and more. We support all common formats.

</td>
<td align="center" width="33%">

### 2️⃣ Choose

Select the AI model and stem configuration that fits your needs.

</td>
<td align="center" width="33%">

### 3️⃣ Download

Get your separated stems in MP3 or high-quality WAV format.

</td>
</tr>
</table>

---

## 🤖 AI Models

Multiple spectrogram/waveform separation models are available through Demucs for different tasks.

### 4-Stem Separation
Separate your music into:
- 🎤 Vocals
- 🥁 Drums
- 🎸 Bass
- 🎹 Other instruments

*Models: htdemucs, htdemucs_ft*

### 6-Stem Separation
Get even more control with:
- 🎤 Vocals
- 🥁 Drums
- 🎸 Bass
- 🎸 Guitar
- 🎹 Piano
- 🎵 Other

*Model: htdemucs_6s*

### 2-Stem Separation
Quick isolation of a single element:
- 🎤 Vocals + Everything Else
- 🥁 Drums + Everything Else
- 🎸 Bass + Everything Else

*Models: htdemucs, htdemucs_ft, htdemucs_6s*

---

## 📸 Screenshots

### Landing Page
<!-- TODO: Add screenshot of landing page -->
![Landing Page](app\static\images\screenshot-landing.png)

### Interactive Demo
<!-- TODO: Add screenshot of demo page with waveform players -->
![Demo Page](app\static\images\screenshot-demo.png)

### Job Creation
<!-- TODO: Add screenshot of job creation page -->
![Create Job](app\static\images\screenshot-new-job.png)

### Results & Playback
<!-- TODO: Add screenshot of job detail page with stem players -->
![Completed Job](app\static\images\screenshot-completed-job.png)

---

## 🔬 About Demucs

Mux Minus is built on top of **[Demucs](https://github.com/facebookresearch/demucs)**, an open-source audio source separation model created by **Facebook AI Research (FAIR)**.

Demucs uses a hybrid approach combining waveform and spectrogram processing with deep learning to achieve state-of-the-art results in music source separation.

### Run Demucs Yourself

If you'd prefer to run Demucs locally on your own computer, you can! Here's how:

#### Installation

```bash
# Install with pip
pip install demucs

# Or with conda
conda install -c conda-forge demucs
```

#### Basic Usage

```bash
# Separate a song into 4 stems (vocals, drums, bass, other)
demucs your-song.mp3

# Use the 6-stem model (adds guitar and piano)
demucs --two-stems=vocals your-song.mp3  # Just vocals + accompaniment
demucs -n htdemucs_6s your-song.mp3      # Full 6-stem separation
```

#### Output

By default, Demucs creates a `separated` folder with subfolders for each model and track:

```
separated/
└── htdemucs/
    └── your-song/
        ├── vocals.wav
        ├── drums.wav
        ├── bass.wav
        └── other.wav
```

For full documentation, visit the [Demucs GitHub repository](https://github.com/facebookresearch/demucs).

---

## 🛠️ Tech Stack

Mux Minus is built with modern, production-ready technologies:

### Frontend
| Technology | Purpose |
|------------|---------|
| **Django** | Web framework & templating |
| **Vanilla JS** | Interactive components |
| **WaveSurfer.js** | Waveform visualization & audio playback |
| **CSS3** | Modern styling with CSS variables |

### Backend
| Technology | Purpose |
|------------|---------|
| **Django** | REST API, user management, administration |
| **FastAPI** | Internal backend service for job processing |
| **Demucs** | AI-powered audio separation |
| **PostgreSQL** | Production database |
| **SQLite** | Development database |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| **Docker** | Containerization |
| **Docker Compose** | Multi-container orchestration |
| **WhiteNoise** | Static file serving |
| **Traefik** | Reverse proxy (production) |

### Payments
| Technology | Purpose |
|------------|---------|
| **Square** | Payment processing |

---

## 📄 License

This project is open source. See the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <sub>Built with ❤️ using <a href="https://github.com/facebookresearch/demucs">Demucs</a> and Copilot <i>(Claude Opus 4.5)</i></sub>
</p>
