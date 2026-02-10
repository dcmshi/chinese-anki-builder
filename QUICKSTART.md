# Quick Start Guide

## ✅ Setup Complete!

Your Anki Chinese Deck Builder is ready to use with **uv**.

### 🎯 What's Installed

- **Python 3.14.3** (managed by uv)
- **Virtual environment** at `.venv/`
- **All dependencies** (jieba, pypinyin, genanki, etc.)

### 🚀 Running the Tool

All commands should use `uv run` to execute within the project environment:

```bash
# Show help
uv run python main.py --help

# Generate a deck from an EPUB file
uv run python main.py --input your_book.epub --deck "My Chinese Deck"

# Generate from PDF
uv run python main.py --input your_book.pdf --deck "Chinese Novel"

# Advanced usage: top 200 words, min frequency 3
uv run python main.py \
  --input book.epub \
  --deck "Advanced Chinese" \
  --top-words 200 \
  --min-freq 3
```

### 📖 Example Workflow

1. **Get a Chinese EPUB or PDF book**
2. **Run the generator:**
   ```bash
   uv run python main.py --input book.epub --deck "My Deck"
   ```
3. **Wait for processing** (downloads CC-CEDICT on first run)
4. **Import the .apkg file** into Anki (found in `output/` directory)

### 🔧 Configuration

Edit `config.yaml` to change defaults:

```yaml
top_words: 150        # Number of words to select
min_frequency: 2      # Minimum word occurrences
enable_tts: false     # TTS audio (not yet implemented)
output_dir: "output"  # Where to save decks
```

### 📊 What Happens During Processing

1. ✅ **Extract** - Reads text from EPUB/PDF
2. ✅ **Clean** - Removes artifacts and normalizes text
3. ✅ **Tokenize** - Segments Chinese text with jieba
4. ✅ **Analyze** - Computes word frequencies
5. ✅ **Select** - Picks top multi-character words
6. ✅ **Dictionary** - Downloads CC-CEDICT (first run only)
7. ✅ **Match** - Finds example sentences
8. ✅ **Generate** - Creates Anki deck (.apkg)

### 🎴 Card Format

**Front:**
- Sentence with target word highlighted

**Back:**
- Word (Chinese characters)
- Pinyin with tones
- English definition
- Chapter tag (if detected)

### 📁 Project Structure

```
anki_deck_builder/
├── .venv/              # Virtual environment (managed by uv)
├── extract/            # EPUB/PDF extraction
├── process/            # Text processing & tokenization
├── anki/               # Deck building
├── utils/              # Utilities
├── data/               # Cached dictionaries (auto-created)
├── output/             # Generated .apkg files (auto-created)
├── main.py             # CLI entry point
└── config.yaml         # Configuration
```

### 🆘 Troubleshooting

**Issue:** "No words selected"
- **Solution:** Lower `--min-freq` (try 1) or increase `--top-words`

**Issue:** "No suitable sentences found"
- **Solution:** Book might be too short or have unusual formatting

**Issue:** Need to reinstall dependencies
```bash
uv sync --reinstall
```

### 🔜 Next Steps

- Try with a Chinese EPUB/PDF book
- Adjust word selection parameters
- Import generated deck into Anki
- Start learning! 📚

### 💡 Tips

- **First run** downloads CC-CEDICT (~10MB), which is cached
- **Processing time** depends on book length (usually 30s - 2min)
- **Start small**: Try with 50-100 words first, then scale up
- **Quality over quantity**: Higher min-freq gives more common words

---

Need help? Check `README.md` for detailed documentation.
