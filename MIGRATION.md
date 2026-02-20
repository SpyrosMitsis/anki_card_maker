# Migration Guide 📦

Upgrading from the original script to the new TUI version.

## What's New? ✨

### Major Improvements

1. **Beautiful TUI Interface**
   - Real-time progress tracking
   - Visual progress bars
   - Color-coded status messages
   - Activity log with timestamps

2. **Checkpoint System**
   - Automatic progress saving
   - Resume from interruptions
   - No lost work on crashes

3. **Better Error Handling**
   - Continues on individual failures
   - Detailed error logging
   - Automatic retry on rate limits

4. **Configuration Management**
   - Save/load settings
   - No more editing code
   - Quick switching between configs

5. **Enhanced Rate Limiting**
   - Time estimates
   - Smarter delays
   - Fewer API errors

## Migration Steps

### 1. Backup Your Current Setup

```bash
# Backup your words file
cp family.txt family.txt.backup

# Backup your audio directory if you want to keep it
cp -r audio audio.backup
```

### 2. New File Structure

The new version splits the monolithic script into modules:

**Old:**
```
your_script.py  (everything in one file)
```

**New:**
```
anki_tui.py     (TUI interface)
core.py         (processing logic)
tts.py          (your existing module)
gemini.py       (your existing module)
```

### 3. Keep Your Existing Modules

The new version still uses your `tts.py` and `gemini.py` files - just keep them in the same directory!

### 4. Configuration Changes

**Old way (hardcoded in script):**
```python
TEST_MODE = False
WORDS_FILE = "./family.txt"
TTS_DELAY = 6.5
```

**New way (config.json or TUI):**
```json
{
  "words_file": "./family.txt",
  "test_mode": false,
  "tts_delay": 6.5
}
```

### 5. Running Your Old Workflow

**Old command:**
```bash
python your_script.py
```

**New TUI:**
```bash
python anki_tui.py
```

**New programmatic (if you want):**
```python
from core import AnkiFlashcardGenerator, GeneratorConfig

config = GeneratorConfig(
    words_file="./family.txt",
    deck_name="Danish vocab",
    model_name="Danish"
)

generator = AnkiFlashcardGenerator(config)
generator.run()
```

## Feature Mapping

### Your Old Script → New Version

| Old | New | Notes |
|-----|-----|-------|
| `TEST_MODE = True` | Toggle "Test Mode" in TUI or `test_mode: true` in config | Same functionality |
| `WORDS_FILE = "./family.txt"` | "Words File" input in TUI | Now configurable without editing code |
| Print statements | Activity Log panel | Better organized, timestamped |
| Exception handling | Checkpoint system | Auto-resume on failures |
| Manual config at bottom | Config panel + JSON file | Save/load configurations |
| No progress tracking | Real-time progress bars | Visual feedback |

## Backwards Compatibility

### Can I Still Use the Old Script?

Yes! The old script will continue to work. The new version is an enhancement, not a replacement.

### Using Existing Audio Files

The new version is compatible with your existing audio directory structure. It can:
- Use existing audio files (skip_existing_audio mode)
- Resume from where you left off (checkpoint system)
- Handle the `.wav.wav` extension issue automatically

### Existing Words Files

Your existing word files work as-is! The format hasn't changed:
```text
# Comments with #
word1
word2
word3
```

## What to Watch Out For ⚠️

### 1. Checkpoint Files

The new version creates `checkpoint.json` files. These are temporary and can be deleted anytime.

### 2. Config Files

If you create `config.json`, it will be loaded automatically on startup. Delete it to start fresh.

### 3. Audio Directory

By default still uses `./audio/` - if you have existing audio, the new version will detect and use it!

### 4. Anki Fields

Your Anki card model must still have these exact field names:
- Word
- Danish Sentence
- Word Translation
- Sentence Translation
- Audio
- Sentence Audio

## Gradual Migration Strategy

### Week 1: Try It Out
- Run new TUI alongside old script
- Test with a small word list (5-10 words)
- Compare results

### Week 2: Daily Use
- Use TUI for new batches
- Keep old script as backup
- Report any issues

### Week 3+: Full Switch
- Use TUI exclusively
- Archive old script
- Enjoy the improvements!

## Rollback Plan

If you need to go back to the old script:

```bash
# Just use your original script
python your_original_script.py

# Your data is still compatible
# Audio files work with both versions
# Word files work with both versions
```

## Getting Help

### Old Script Issues
- Check your original script documentation
- Review error messages in terminal

### New TUI Issues  
- Check the Activity Log in the TUI
- Review `checkpoint.json` for state
- See QUICKSTART.md for common issues

## Pro Tips 💡

1. **Start Small**: Test with 3-5 words first
2. **Save Configs**: Use config files for different word sets
3. **Check Logs**: The activity log shows everything
4. **Use Checkpoints**: Let it save progress automatically
5. **Enable Skip Existing**: Speed up re-runs dramatically

---

**Questions?** Check the README.md for detailed documentation!

Happy migrating! 🚀
