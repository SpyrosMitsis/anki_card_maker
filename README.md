# Anki Danish Vocabulary Generator 🇩🇰

A beautiful TUI (Text User Interface) application for automatically generating Anki flashcards with audio for Danish vocabulary learning.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)

## ✨ Features

- 🎨 **Beautiful TUI** - Clean, modern text-based interface using Textual
- 🤖 **AI-Powered** - Uses Gemini AI to generate natural example sentences
- 🎤 **Text-to-Speech** - Automatic Danish audio generation with rate limiting
- 💾 **Checkpoint System** - Resume interrupted sessions without losing progress
- 📊 **Real-time Progress** - Visual progress bars and detailed activity logs
- ⚙️ **Configuration** - Save and load settings for quick reuse
- 🔄 **Smart Recovery** - Automatic retry on rate limits and network errors
- 🧪 **Test Mode** - Try with existing audio before generating new content

## 📋 Prerequisites

- Python 3.8 or higher
- Anki Desktop application installed and running
- AnkiConnect add-on installed in Anki
- Google Gemini API access (for content generation)
- Google Cloud TTS API access (for audio generation)

## 🚀 Installation

1. **Clone or download this repository**

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Install AnkiConnect**
   - Open Anki
   - Go to Tools → Add-ons → Get Add-ons
   - Enter code: `2055492159`
   - Restart Anki

4. **Set up API credentials**
   - Create your API key files for Gemini and TTS
   - Place them in the appropriate locations as expected by your `tts.py` and `gemini.py` modules

5. **Create your Anki card template**
   - In Anki, create a new note type called "Danish" (or your preferred name)
   - Add these fields:
     - Word
     - Danish Sentence
     - Word Translation
     - Sentence Translation
     - Audio
     - Sentence Audio

## 📖 Usage

### Quick Start

1. **Create a words file** (e.g., `words.txt`):
```text
# Danish vocabulary words - one per line
# Lines starting with # are comments

hund
kat
hus
bog
bil
```

2. **Run the TUI application**:
```bash
python anki_tui.py
```

3. **Configure your settings** in the left panel:
   - Words File: Path to your word list
   - Anki Deck: Target deck name
   - Card Model: Your note type name
   - Audio Directory: Where to store audio files

4. **Click "Start Processing"** and watch the magic happen! ✨

### Configuration File

Save your settings to `config.json` for quick reuse:

```json
{
  "words_file": "./words.txt",
  "deck_name": "Danish vocab",
  "model_name": "Danish",
  "audio_dir": "./audio",
  "skip_existing_audio": false,
  "test_mode": false
}
```

Use the "Save Config" and "Load Config" buttons in the TUI.

### Command Line (Original Script)

You can still use the original script for automated workflows:

```bash
python your_original_script.py
```

## 🎯 Features Explained

### Checkpoint System
- Automatically saves progress after each word
- Resume from where you left off if interrupted
- Checkpoint file: `checkpoint.json`

### Rate Limiting
- Built-in delays between TTS requests (default: 6.5 seconds)
- Automatic retry on rate limit errors (429)
- Estimated time remaining display

### Error Handling
- Continues processing even if individual words fail
- Detailed error logging
- Summary of successes and failures

### Test Mode
- Use existing audio files without generating new ones
- Perfect for testing Anki integration
- Saves API costs during development

### Skip Existing Audio
- Checks if audio already exists before generating
- Speeds up re-runs for partial updates
- Useful when adding to existing word lists

## 📁 File Structure

```
.
├── anki_tui.py          # Main TUI application
├── core.py              # Core processing logic
├── tts.py               # Text-to-speech integration
├── gemini.py            # Gemini AI integration
├── requirements.txt     # Python dependencies
├── config.json          # Configuration (created by app)
├── checkpoint.json      # Progress checkpoint (created automatically)
├── words.txt            # Your word list
├── audio/               # Generated audio files
└── README.md           # This file
```

## 🎨 TUI Interface

```
┌─ Anki Danish Vocabulary Generator ────────────────────────────────────┐
│                                                                        │
│ ┌─ Configuration ─┐  ┌─ Status ──────────────────────────────────┐  │
│ │                  │  │ 🎤 Generating Audio                        │  │
│ │ Words File       │  │                                            │  │
│ │ Anki Deck        │  │ Total Words: 10                           │  │
│ │ Card Model       │  │ Processed: 7                              │  │
│ │ Audio Dir        │  │ Failed: 0                                 │  │
│ │                  │  │ Current: hund                             │  │
│ │ Skip Existing    │  │ Est. Time: 2m 30s                         │  │
│ │ Test Mode        │  └────────────────────────────────────────────┘  │
│ │                  │                                                  │
│ └──────────────────┘  ┌─ Progress ────────────────────────────────┐  │
│                       │ Overall Progress                           │  │
│                       │ ████████████░░░░░░░░░░ 70%                │  │
│                       │                                            │  │
│                       │ Current Operation                          │  │
│                       │ ███████████████████░░ 95%                 │  │
│                       └────────────────────────────────────────────┘  │
│                                                                        │
│                       ┌─ Activity Log ─────────────────────────────┐  │
│                       │ 14:32:15 🚀 Starting generation...         │  │
│                       │ 14:32:16 📖 Loaded 10 words                │  │
│                       │ 14:32:17 ✅ Generated content for: hund    │  │
│                       │ 14:32:24 🔊 Generated audio for word       │  │
│                       └────────────────────────────────────────────┘  │
│                                                                        │
│              [🚀 Start] [⏹️ Cancel] [📋 Load] [💾 Save]              │
└────────────────────────────────────────────────────────────────────────┘
```

## ⌨️ Keyboard Shortcuts

- `s` - Start processing
- `c` - Cancel current operation
- `q` - Quit application

## ⚠️ Troubleshooting

### "Anki media directory not found"
- Make sure Anki is installed
- Check that AnkiConnect is installed and enabled
- Verify Anki is running

### "Rate limit exceeded"
- The app will automatically retry after 20 seconds
- Adjust `tts_delay` in config for slower processing
- Consider processing words in smaller batches

### "Could not parse JSON response"
- Check your Gemini API key is valid
- Verify network connection
- The word will be skipped and logged

### Audio files not playing in Anki
- Ensure audio files are in Anki's media directory
- Check file permissions
- Verify file format is .wav

## 🔧 Advanced Configuration

Edit `core.py` to customize:

- **Gemini prompt** - Modify `GEMINI_PROMPT` for different sentence styles
- **TTS delay** - Change `tts_delay` in `GeneratorConfig`
- **Retry logic** - Adjust retry delays and attempts
- **File naming** - Customize `normalize_filename()` function

## 📝 Tips & Best Practices

1. **Start small** - Test with 3-5 words first
2. **Use meaningful names** - Organize words by topic/theme
3. **Regular backups** - Save your word lists and config files
4. **Monitor rate limits** - Process during off-peak hours for APIs
5. **Review cards** - Check generated content before studying

## 🤝 Contributing

Suggestions and improvements welcome! This is a personal learning tool that's been polished for sharing.

## 📄 License

This project is provided as-is for educational purposes. Respect API usage limits and terms of service.

## 🙏 Credits

- Built with [Textual](https://github.com/Textualize/textual)
- Uses Google Gemini AI for content generation
- Uses Google Cloud Text-to-Speech
- Integrates with [AnkiConnect](https://github.com/FooSoft/anki-connect)

## 🆘 Support

If you encounter issues:
1. Check the activity log in the TUI for detailed errors
2. Review `checkpoint.json` for progress state
3. Verify all API keys and credentials
4. Ensure Anki and AnkiConnect are running

---

**Happy Learning! 🎓** Made with ❤️ for Danish language learners
