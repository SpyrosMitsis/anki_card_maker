# Quick Start Guide 🚀

Get up and running in 5 minutes!

## Step 1: Setup Files

Copy the example files:
```bash
cp words.example.txt words.txt
cp config.example.json config.json
```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

You'll also need:
```bash
pip install py-ankiconnect google-generativeai google-cloud-texttospeech
```

## Step 3: Configure API Keys

Make sure your `tts.py` and `gemini.py` modules are configured with your API keys.

## Step 4: Set Up Anki

1. Install Anki if not already installed
2. Install AnkiConnect add-on (code: `2055492159`)
3. Create a note type called "Danish" with these fields:
   - Word
   - Danish Sentence  
   - Word Translation
   - Sentence Translation
   - Audio
   - Sentence Audio
4. Create a deck called "Danish vocab"
5. **Make sure Anki is running!**

## Step 5: Add Your Words

Edit `words.txt` and add Danish words, one per line:
```text
hund
kat
familie
arbejde
```

## Step 6: Run the App

```bash
python anki_tui.py
```

## Step 7: Start Processing

1. Review the configuration in the left panel
2. Click "🚀 Start Processing"
3. Watch the progress!

## Tips

- Start with just 3-5 words to test everything works
- The first audio generation takes time due to rate limiting
- You can cancel and resume - progress is saved automatically
- Enable "Skip Existing Audio" to speed up re-runs

## Common Issues

**"Anki media directory not found"**
→ Make sure Anki is running!

**"Rate limit exceeded"**  
→ The app will automatically retry. Be patient!

**"Module not found: tts or gemini"**
→ Make sure your original `tts.py` and `gemini.py` files are in the same directory

---

That's it! You're ready to generate flashcards. Happy learning! 🎓
