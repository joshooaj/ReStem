# Create Job Page Update Summary

## What Was Added

The create_job.html template has been completely updated to support the new transcription features.

### New Job Type Selector (appears first)

The page now displays three radio card options at the top:

1. **🎵 Audio Separation** (1 credit)
   - Separate music into vocals, drums, bass, and other instruments
   
2. **📝 Speech Transcription** (1 credit)  
   - Convert speech to text, generate subtitles, or timestamped transcripts
   
3. **🎤 Lyrics Generation** (2 credits - marked with "2 Steps" badge)
   - Extract timestamped lyrics from songs (isolates vocals first)

### Dynamic Form Behavior

Based on the selected job type, the form dynamically shows different options:

#### When "Audio Separation" is selected:
- Shows: Separation Type (Full/Two-Stem)
- Shows: Model Selection (4-Stem/4-Stem Fine-tuned/6-Stem)
- Shows: Output Format (MP3/WAV)
- File hint: "MP3, WAV, FLAC, OGG, M4A, AAC (max 100MB)"
- Button: "Start Processing (1 credit)"

#### When "Speech Transcription" is selected:
- Shows: Transcription Type selector with 3 options:
  - Basic Text (plain .txt file)
  - Timestamped Transcript (.json file with timestamps)
  - Subtitle File (generates SRT or VTT)
- Shows: Subtitle Format selector (SRT/VTT) - only when "Subtitle File" is chosen
- Shows: Language input field (optional, for language specification)
- File hint: "Audio/Video: MP3, WAV, MP4, MKV, AVI (max 5GB)"
- Button: "Start Processing (1 credit)"

#### When "Lyrics Generation" is selected:
- Shows: Pipeline explanation card describing the 2-step process:
  1. Isolate vocals from music using Demucs
  2. Generate timestamped lyrics (LRC format) from vocals
- Shows: Language input field (optional)
- File hint: "Audio: MP3, WAV, FLAC, OGG, M4A (max 5GB)"
- Button: "Start Processing (2 credits)"

### Key UI Features

1. **File size hints update** based on job type (100MB for separation, 5GB for transcription/lyrics)
2. **Credit cost updates** in the submit button (1 or 2 credits)
3. **Processing time hints update** based on job type
4. **Output preview** in sidebar adapts to job type
5. **Video format support** is now visible for transcription jobs

### Visual Structure

```
┌─────────────────────────────────────────┐
│ 🎯 Job Type                              │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │🎵 Audio  │ │📝 Speech │ │🎤 Lyrics │ │
│ │Separation│ │Transcript│ │Generation│ │
│ │1 credit  │ │1 credit  │ │2 credits │ │
│ └──────────┘ └──────────┘ └──────────┘ │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ 📁 Upload File                           │
│ [Drag & drop area with dynamic hint]    │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ [Dynamic options based on job type]     │
│ - Separation: type, model, format       │
│ - Transcription: type, format, language │
│ - Lyrics: language only                 │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ [Start Processing (X credits)] Button   │
└─────────────────────────────────────────┘
```

## JavaScript Enhancements

- Job type selection triggers show/hide of relevant option sections
- File size limits and hints update dynamically
- Credit cost display updates in submit button
- Transcription format selector only shows for subtitle type
- All event handlers safely check for element existence
- Output preview sidebar intelligently handles all job types

## User Experience

Users now have a clear, intuitive interface to:
1. Choose what type of processing they want
2. See exactly how many credits it will cost
3. Upload appropriate file types with correct size limits
4. Configure type-specific options
5. Understand what they'll receive as output

The form provides immediate visual feedback and guidance throughout the job creation process.
