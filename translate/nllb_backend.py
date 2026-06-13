"""NLLB-200 translation backend via CTranslate2 (higher-quality offline neural MT).

This is a prototype higher-quality alternative to the Argos backend. It runs
Meta's NLLB-200 model on the same CTranslate2 inference engine that Argos
already depends on, but uses a larger multilingual model for noticeably better
zh->en sentence translation.

The heavy optional dependencies (transformers, huggingface_hub) and the model
download are intentionally lazy: this module imports cleanly without them, and
``is_available()`` reports False so the TranslationManager simply skips it and
falls back to Argos. Install the extras to opt in:

    uv sync --extra nllb
"""

import os
from typing import Optional, Dict, Any

from translate.base import TranslationBackend
from utils.file_utils import get_data_dir


# NLLB uses FLORES-200 language codes (e.g. "zho_Hans", "eng_Latn") rather than
# the short ISO codes the rest of the pipeline passes around.
NLLB_LANG_CODES = {
    "zh": "zho_Hans",
    "zh-hans": "zho_Hans",
    "zh-hant": "zho_Hant",
    "en": "eng_Latn",
}

# CTranslate2-converted NLLB model (no PyTorch needed at inference time). The
# tokenizer is loaded from the canonical Facebook repo. Both are overridable via
# config or environment so users can pick a larger model (e.g. 1.3B/3.3B).
DEFAULT_CT2_MODEL_REPO = "entai2965/nllb-200-distilled-600M-ctranslate2"
DEFAULT_TOKENIZER_REPO = "facebook/nllb-200-distilled-600M"


class NLLBTranslateBackend(TranslationBackend):
    """NLLB-200 backend running on CTranslate2 for offline neural MT."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.translator = None
        self.tokenizer = None

        self.model_repo = (
            self.config.get("nllb_model_repo")
            or os.environ.get("NLLB_CT2_MODEL")
            or DEFAULT_CT2_MODEL_REPO
        )
        self.tokenizer_repo = (
            self.config.get("nllb_tokenizer_repo")
            or os.environ.get("NLLB_TOKENIZER")
            or DEFAULT_TOKENIZER_REPO
        )
        # int8 keeps the 600M model small/fast on CPU; override for GPU/quality.
        self.device = self.config.get("nllb_device", "cpu")
        self.compute_type = self.config.get("nllb_compute_type", "int8")

    def is_available(self) -> bool:
        """Available only when the optional inference + tokenizer deps import."""
        try:
            import ctranslate2  # noqa: F401
            import transformers  # noqa: F401
            import huggingface_hub  # noqa: F401

            return True
        except ImportError:
            return False

    def initialize(self) -> bool:
        """Download (first run) and load the NLLB model + tokenizer."""
        try:
            import ctranslate2
            import transformers
            from huggingface_hub import snapshot_download

            model_dir = get_data_dir() / "nllb_ct2_model"
            if not (model_dir / "model.bin").exists():
                print(f"Downloading NLLB CT2 model '{self.model_repo}' (first run, large)...")
                snapshot_download(repo_id=self.model_repo, local_dir=str(model_dir))
                print("NLLB model downloaded.")
            else:
                print("Using cached NLLB CT2 model")

            self.translator = ctranslate2.Translator(
                str(model_dir), device=self.device, compute_type=self.compute_type
            )
            self.tokenizer = transformers.AutoTokenizer.from_pretrained(self.tokenizer_repo)
            self._initialized = True
            return True

        except ImportError as e:
            print(f"NLLB backend unavailable (missing optional deps): {e}")
            return False
        except Exception as e:
            print(f"Error initializing NLLB backend: {e}")
            return False

    def translate(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """Translate a sentence with NLLB-200.

        Args:
            text: Source text (Chinese by default)
            source_lang: Short source language code (mapped to a FLORES-200 code)
            target_lang: Short target language code (mapped to a FLORES-200 code)

        Returns:
            Translated text, or the original text on failure
        """
        if not text or not text.strip():
            return ""

        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("NLLB backend not initialized")

        src_code = NLLB_LANG_CODES.get(source_lang.lower(), "zho_Hans")
        tgt_code = NLLB_LANG_CODES.get(target_lang.lower(), "eng_Latn")

        try:
            # Setting src_lang makes encode() prepend the source language token.
            self.tokenizer.src_lang = src_code
            source_tokens = self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(text))

            # The decoder is forced to start in the target language.
            results = self.translator.translate_batch(
                [source_tokens], target_prefix=[[tgt_code]]
            )
            target_tokens = results[0].hypotheses[0]

            # Drop the leading target-language token before decoding.
            if target_tokens and target_tokens[0] == tgt_code:
                target_tokens = target_tokens[1:]

            return self.tokenizer.decode(
                self.tokenizer.convert_tokens_to_ids(target_tokens)
            ).strip()

        except Exception as e:
            print(f"NLLB translation error: {e}")
            return text  # Fall back to original text

    def get_name(self) -> str:
        return "NLLB-200 (CTranslate2, Offline Neural MT)"

    def requires_internet(self) -> bool:
        """Offline after the one-time model download."""
        return False

    def get_quality_score(self) -> int:
        """Higher than Argos (80): larger multilingual model, better zh->en."""
        return 90
