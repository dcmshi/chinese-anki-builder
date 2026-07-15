"""HY-MT1.5 translation backend via llama.cpp (highest-quality offline neural MT).

Tencent's Hunyuan-MT-7B won WMT25 (first place in 30 of 31 language pairs);
its successor HY-MT1.5 (open-sourced 2025-12-30) is the current open offline
state of the art for zh->en. The default here is the 1.8B GGUF build, whose
quantized footprint (~1GB) is comparable to the NLLB distilled-600M int8
model while translating literary Chinese far better. The 7B build is a
config/env override away for users with the RAM for it.

The heavy optional dependencies (llama-cpp-python, huggingface_hub) and the
model download are intentionally lazy: this module imports cleanly without
them, and ``is_available()`` reports False so the TranslationManager simply
skips it and falls back to NLLB/Argos. Install the extras to opt in:

    uv sync --extra hymt
"""

import os
from typing import List, Optional, Dict, Any

from translate.base import TranslationBackend
from utils.file_utils import get_data_dir


# Official GGUF builds published by Tencent. The filename is a glob matched
# against the repo contents (llama-cpp-python resolves it), so a quant level
# is picked without hardcoding exact file names.
DEFAULT_GGUF_REPO = "tencent/HY-MT1.5-1.8B-GGUF"
DEFAULT_GGUF_FILE = "*Q4_K_M.gguf"

# Language names for the official prompt templates. HY-MT's model card uses a
# Chinese instruction for pairs involving Chinese and an English instruction
# otherwise; the tuple is (english_name, chinese_name).
LANG_NAMES = {
    "zh": ("Chinese", "中文"),
    "zh-hans": ("Chinese", "中文"),
    "zh-hant": ("Traditional Chinese", "繁体中文"),
    "en": ("English", "英文"),
}


def build_prompt(text: str, source_lang: str, target_lang: str) -> str:
    """Build the official HY-MT translation prompt for a language pair.

    Chinese-involved pairs use the Chinese template, others the English one,
    matching the model card. Exposed at module level for testability.
    """
    src = source_lang.lower()
    tgt = target_lang.lower()
    en_name, zh_name = LANG_NAMES.get(tgt, (target_lang, target_lang))

    if src.startswith("zh") or tgt.startswith("zh"):
        return f"把下面的文本翻译成{zh_name}，不要额外解释。\n\n{text}"
    return f"Translate the following segment into {en_name}, without additional explanation.\n\n{text}"


class HYMTTranslateBackend(TranslationBackend):
    """HY-MT1.5 backend running a GGUF build on llama.cpp for offline MT."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.llm = None

        self.model_repo = (
            self.config.get("hymt_model_repo")
            or os.environ.get("HYMT_GGUF_REPO")
            or DEFAULT_GGUF_REPO
        )
        self.model_file = (
            self.config.get("hymt_model_file")
            or os.environ.get("HYMT_GGUF_FILE")
            or DEFAULT_GGUF_FILE
        )
        # Pin for reproducible downloads ("same input + config -> same deck").
        # None means the repo's current head; once downloaded, runs are stable.
        self.revision = self.config.get("hymt_revision") or os.environ.get("HYMT_REVISION")
        # Sentences here are <=100 chars, so a small context is plenty.
        self.n_ctx = int(self.config.get("hymt_n_ctx", 2048))
        self.n_gpu_layers = int(self.config.get("hymt_n_gpu_layers", 0))

    def is_available(self) -> bool:
        """Available only when the optional llama.cpp + hub deps import."""
        try:
            import llama_cpp  # noqa: F401
            import huggingface_hub  # noqa: F401

            return True
        except ImportError:
            return False

    def initialize(self) -> bool:
        """Download (first run) and load the HY-MT GGUF model."""
        try:
            from llama_cpp import Llama

            model_dir = get_data_dir() / "hymt_model"
            print(f"Loading HY-MT model '{self.model_repo}' ({self.model_file})...")
            print("(first run downloads the GGUF, ~1GB for the 1.8B Q4_K_M)")
            self.llm = Llama.from_pretrained(
                repo_id=self.model_repo,
                filename=self.model_file,
                revision=self.revision,
                local_dir=str(model_dir),
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
            )
            self._initialized = True
            return True

        except ImportError as e:
            print(f"HY-MT backend unavailable (missing optional deps): {e}")
            return False
        except Exception as e:
            print(f"Error initializing HY-MT backend: {e}")
            return False

    def translate(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """Translate a sentence with HY-MT1.5.

        Args:
            text: Source text (Chinese by default)
            source_lang: Short source language code
            target_lang: Short target language code

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

        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("HY-MT backend not initialized")

        prompt = build_prompt(text, source_lang, target_lang)

        # Sampling parameters recommended by the Hunyuan-MT model card.
        result = self.llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            top_p=0.6,
            top_k=20,
            repeat_penalty=1.05,
            max_tokens=512,
        )
        translation = result["choices"][0]["message"]["content"].strip()

        if translation == text.strip():
            raise RuntimeError("HY-MT echoed the source text")
        return translation

    def translate_batch(
        self, texts: List[str], source_lang: str = "zh", target_lang: str = "en"
    ) -> List[str]:
        """Sequential batch: llama.cpp decodes one prompt at a time on CPU.

        Exists so the manager's batch path works uniformly; the per-call
        model state is reused, which is where the actual speedup lives.
        """
        return [self.translate(text, source_lang, target_lang) for text in texts]

    def get_name(self) -> str:
        return "HY-MT1.5 (llama.cpp, Offline Neural MT)"

    def requires_internet(self) -> bool:
        """Offline after the one-time model download."""
        return False

    def get_quality_score(self) -> int:
        """Above NLLB (90): WMT25-winning line, zh-centric training."""
        return 95

    def cleanup(self):
        """Release the llama.cpp model."""
        self.llm = None
        self._initialized = False
