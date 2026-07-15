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
from typing import List, Optional, Dict, Any

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
        # Pins for reproducible downloads ("same input + config -> same deck").
        # None means the repo's current head; once cached, runs are stable.
        self.model_revision = self.config.get("nllb_model_revision") or os.environ.get(
            "NLLB_CT2_REVISION"
        )
        self.tokenizer_revision = self.config.get("nllb_tokenizer_revision") or os.environ.get(
            "NLLB_TOKENIZER_REVISION"
        )
        # int8 keeps the 600M model small/fast on CPU; override for GPU/quality.
        self.device = self.config.get("nllb_device", "cpu")
        self.compute_type = self.config.get("nllb_compute_type", "int8")
        # Decoding guards: NLLB is prone to repetition loops on noisy input,
        # and quality degrades sharply past its training sentence lengths.
        self.beam_size = int(self.config.get("nllb_beam_size", 4))
        self.no_repeat_ngram_size = int(self.config.get("nllb_no_repeat_ngram_size", 3))
        self.max_input_length = int(self.config.get("nllb_max_input_length", 256))
        self.max_decoding_length = int(self.config.get("nllb_max_decoding_length", 256))

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
                snapshot_download(
                    repo_id=self.model_repo,
                    local_dir=str(model_dir),
                    revision=self.model_revision,
                )
                print("NLLB model downloaded.")
            else:
                print("Using cached NLLB CT2 model")

            self.translator = ctranslate2.Translator(
                str(model_dir), device=self.device, compute_type=self.compute_type
            )
            self.tokenizer = transformers.AutoTokenizer.from_pretrained(
                self.tokenizer_repo, revision=self.tokenizer_revision
            )
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
            Translated text

        Raises:
            RuntimeError on failure. Never returns the source text: a
            non-empty return is treated as success by TranslationManager and
            cached, which would silently disable its fallback chain and put
            the Chinese sentence on the card as its own "translation".
        """
        if not text or not text.strip():
            return ""

        return self.translate_batch([text], source_lang, target_lang)[0]

    def translate_batch(
        self, texts: List[str], source_lang: str = "zh", target_lang: str = "en"
    ) -> List[str]:
        """Translate many sentences in one CTranslate2 batch call.

        Batching is where CT2 earns its keep: one call for N sentences is
        several times faster than N single-sentence calls on CPU. Empty
        inputs map to "" without touching the model. Same raise-don't-echo
        failure contract as translate().
        """
        if not texts:
            return []

        # Preserve positions of empty inputs; only real text hits the model.
        indexed = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        results = [""] * len(texts)
        if not indexed:
            return results

        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("NLLB backend not initialized")

        src_code = NLLB_LANG_CODES.get(source_lang.lower(), "zho_Hans")
        tgt_code = NLLB_LANG_CODES.get(target_lang.lower(), "eng_Latn")

        # Setting src_lang makes encode() prepend the source language token.
        self.tokenizer.src_lang = src_code
        batch_tokens = [
            self.tokenizer.convert_ids_to_tokens(self.tokenizer.encode(t)) for _, t in indexed
        ]

        # The decoder is forced to start in the target language. Length caps
        # and the no-repeat guard keep NLLB from looping on odd input.
        batch_results = self.translator.translate_batch(
            batch_tokens,
            target_prefix=[[tgt_code]] * len(batch_tokens),
            beam_size=self.beam_size,
            no_repeat_ngram_size=self.no_repeat_ngram_size,
            max_input_length=self.max_input_length,
            max_decoding_length=self.max_decoding_length,
        )

        for (i, _), result in zip(indexed, batch_results):
            target_tokens = result.hypotheses[0]
            # Drop the leading target-language token before decoding.
            if target_tokens and target_tokens[0] == tgt_code:
                target_tokens = target_tokens[1:]
            results[i] = self.tokenizer.decode(
                self.tokenizer.convert_tokens_to_ids(target_tokens)
            ).strip()

        return results

    def get_name(self) -> str:
        return "NLLB-200 (CTranslate2, Offline Neural MT)"

    def requires_internet(self) -> bool:
        """Offline after the one-time model download."""
        return False

    def get_quality_score(self) -> int:
        """Higher than Argos (80): larger multilingual model, better zh->en."""
        return 90
