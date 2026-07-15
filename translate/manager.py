"""Translation manager for coordinating multiple backends."""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from translate.base import TranslationBackend
from translate.hymt_backend import HYMTTranslateBackend
from translate.nllb_backend import NLLBTranslateBackend
from translate.argos_backend import ArgosTranslateBackend
from translate.cedict_backend import CEDICTBackend


def _normalize_name(name: str) -> str:
    """Lowercase a backend name and strip punctuation for loose matching.

    Lets config say `preferred_backend: hymt` (or nllb/argos/cedict) without
    reproducing the exact display name.
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


class TranslationManager:
    """
    Manages multiple translation backends with automatic fallback.

    Tries backends in order of quality score, falling back if one fails.
    """

    def __init__(
        self,
        backends: Optional[List[TranslationBackend]] = None,
        config: Optional[Dict[str, Any]] = None,
        cache_path: Optional[Path] = None,
    ):
        """
        Initialize translation manager.

        Args:
            backends: List of translation backends (auto-creates default if None)
            config: Config dict passed through to the default backends (model
                repo overrides, decoding params, preferred_backend, ...)
            cache_path: Optional JSON file for a persistent translation cache
                that survives across runs (keyed by backend + language pair +
                text, so a backend upgrade never serves stale output)
        """
        self.config = config or {}

        if backends is None:
            # Default chain by quality: HY-MT (opt-in, highest) -> NLLB
            # (opt-in) -> Argos -> CEDICT. The opt-in backends only activate
            # if their optional deps are installed; otherwise is_available()
            # is False and the manager skips them.
            self.backends = [
                HYMTTranslateBackend(self.config),
                NLLBTranslateBackend(self.config),
                ArgosTranslateBackend(self.config),
                CEDICTBackend(self.config),
            ]
        else:
            self.backends = backends

        # Sort by quality score (highest first)
        self.backends.sort(key=lambda b: b.get_quality_score(), reverse=True)

        self.active_backend: Optional[TranslationBackend] = None

        # Cache of (text, source_lang, target_lang) -> translation. Many word
        # cards reuse the same example sentence, so this avoids re-translating.
        self._cache: Dict[tuple, str] = {}

        # Persistent cross-run cache: {backend_name: {"src->tgt": {text: t}}}.
        # Keyed by backend so installing a better backend re-translates
        # instead of serving the old backend's output.
        self._cache_path = Path(cache_path) if cache_path else None
        self._persistent: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._cache_dirty = False
        if self._cache_path and self._cache_path.exists():
            try:
                with open(self._cache_path, "r", encoding="utf-8") as f:
                    self._persistent = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Warning: ignoring unreadable translation cache: {e}")
                self._persistent = {}

    def initialize(self, prefer_offline: bool = True) -> bool:
        """
        Initialize translation backends.

        Args:
            prefer_offline: Prefer offline backends (default: True)

        Returns:
            True if at least one backend initialized successfully
        """
        # An explicitly preferred backend is tried first regardless of its
        # quality score; if it fails to initialize, the normal quality-ranked
        # order takes over.
        preferred = _normalize_name(str(self.config.get("preferred_backend") or ""))
        ordered = list(self.backends)
        if preferred:
            matches = [b for b in ordered if preferred in _normalize_name(b.get_name())]
            if matches:
                ordered = matches + [b for b in ordered if b not in matches]
            else:
                print(f"Warning: no backend matches preferred_backend '{preferred}'")

        initialized_count = 0

        for backend in ordered:
            # Skip online backends if preferring offline
            if prefer_offline and backend.requires_internet():
                print(f"Skipping {backend.get_name()} (requires internet)")
                continue

            # Check availability
            if not backend.is_available():
                print(f"Skipping {backend.get_name()} (not available)")
                continue

            # Try to initialize
            try:
                if backend.initialize():
                    print(f"✓ Initialized: {backend.get_name()}")
                    initialized_count += 1

                    # Set as active if first successful backend
                    if self.active_backend is None:
                        self.active_backend = backend
                        print(f"→ Using: {backend.get_name()}")
                else:
                    print(f"✗ Failed to initialize: {backend.get_name()}")
            except Exception as e:
                print(f"✗ Error initializing {backend.get_name()}: {e}")

        return initialized_count > 0

    def set_cedict(self, cedict: Dict):
        """
        Set CEDICT dictionary for CEDICT backend.

        Args:
            cedict: CC-CEDICT dictionary
        """
        for backend in self.backends:
            if isinstance(backend, CEDICTBackend):
                backend.set_cedict(cedict)

    def _persistent_get(self, backend_name: str, pair: str, text: str) -> Optional[str]:
        return self._persistent.get(backend_name, {}).get(pair, {}).get(text)

    def _persistent_put(self, backend_name: str, pair: str, text: str, translation: str):
        if self._cache_path is None:
            return
        self._persistent.setdefault(backend_name, {}).setdefault(pair, {})[text] = translation
        self._cache_dirty = True

    def save_cache(self):
        """Write the persistent cache to disk if anything changed."""
        if self._cache_path is None or not self._cache_dirty:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(self._persistent, f, ensure_ascii=False, indent=1)
            self._cache_dirty = False
        except OSError as e:
            print(f"Warning: could not write translation cache: {e}")

    def _store_success(
        self, backend: TranslationBackend, cache_key: tuple, pair: str, text: str, result: str
    ):
        """Record a successful translation in both cache layers."""
        self._cache[cache_key] = result
        self._persistent_put(backend.get_name(), pair, text, result)

    def _fallback_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Try every initialized non-active backend in quality order."""
        cache_key = (text, source_lang, target_lang)
        pair = f"{source_lang}->{target_lang}"

        for backend in self.backends:
            if backend == self.active_backend:
                continue  # Already tried

            if not backend.is_initialized():
                continue

            try:
                result = backend.translate(text, source_lang, target_lang)
                if result and result.strip():
                    print(f"Used fallback: {backend.get_name()}")
                    self._store_success(backend, cache_key, pair, text, result)
                    return result
            except Exception as e:
                print(f"Fallback {backend.get_name()} failed: {e}")

        # If all failed, return empty string (not cached, so a later retry can succeed)
        return ""

    def translate(
        self,
        text: str,
        source_lang: str = "zh",
        target_lang: str = "en",
        fallback: bool = True,
    ) -> str:
        """
        Translate text using available backends.

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            fallback: Try fallback backends if primary fails (default: True)

        Returns:
            Translated text
        """
        if not text or not text.strip():
            return ""

        # Return a previously computed translation for identical input
        cache_key = (text, source_lang, target_lang)
        if cache_key in self._cache:
            return self._cache[cache_key]

        pair = f"{source_lang}->{target_lang}"

        # Try active backend first (consulting its persistent cache)
        if self.active_backend:
            cached = self._persistent_get(self.active_backend.get_name(), pair, text)
            if cached:
                self._cache[cache_key] = cached
                return cached
            try:
                result = self.active_backend.translate(text, source_lang, target_lang)
                if result and result.strip():
                    self._store_success(self.active_backend, cache_key, pair, text, result)
                    return result
            except Exception as e:
                print(f"Translation failed with {self.active_backend.get_name()}: {e}")

        if fallback:
            return self._fallback_translate(text, source_lang, target_lang)

        return ""

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str = "zh",
        target_lang: str = "en",
        fallback: bool = True,
    ) -> List[str]:
        """
        Translate many texts in one pass, preserving order.

        Deduplicates inputs, serves cache hits, and sends only the remaining
        unique texts to the active backend's translate_batch (a single
        CTranslate2 call for NLLB — several times faster than per-sentence
        calls). Any text the batch fails on goes through the per-item
        fallback chain, so partial failures degrade exactly like translate().

        Args:
            texts: Texts to translate
            source_lang: Source language code
            target_lang: Target language code
            fallback: Try fallback backends for failed items (default: True)

        Returns:
            Translations in the same order as the inputs ("" on failure)
        """
        results: List[Optional[str]] = [None] * len(texts)
        pair = f"{source_lang}->{target_lang}"

        # Resolve empties and cache hits; collect indices per unique pending text.
        pending: Dict[str, List[int]] = {}
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = ""
                continue
            cache_key = (text, source_lang, target_lang)
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
                continue
            if self.active_backend:
                cached = self._persistent_get(self.active_backend.get_name(), pair, text)
                if cached:
                    self._cache[cache_key] = cached
                    results[i] = cached
                    continue
            pending.setdefault(text, []).append(i)

        # One batch call for everything the caches couldn't answer.
        if pending and self.active_backend:
            unique_texts = list(pending.keys())
            try:
                batch_out = self.active_backend.translate_batch(
                    unique_texts, source_lang, target_lang
                )
            except Exception as e:
                print(f"Batch translation failed with {self.active_backend.get_name()}: {e}")
                batch_out = None

            if batch_out is not None:
                for text, result in zip(unique_texts, batch_out):
                    if result and result.strip():
                        cache_key = (text, source_lang, target_lang)
                        self._store_success(
                            self.active_backend, cache_key, pair, text, result
                        )
                        for i in pending[text]:
                            results[i] = result

        # Whatever is still unresolved goes through the per-item fallback chain.
        for text, indices in pending.items():
            if results[indices[0]] is not None:
                continue
            result = self._fallback_translate(text, source_lang, target_lang) if fallback else ""
            for i in indices:
                results[i] = result

        self.save_cache()
        return [r if r is not None else "" for r in results]

    def get_active_backend_name(self) -> str:
        """Get the name of the currently active backend."""
        if self.active_backend:
            return self.active_backend.get_name()
        return "None"

    def list_backends(self) -> List[Dict[str, Any]]:
        """
        List all available backends with their status.

        Returns:
            List of backend info dictionaries
        """
        return [
            {
                "name": backend.get_name(),
                "initialized": backend.is_initialized(),
                "quality": backend.get_quality_score(),
                "offline": not backend.requires_internet(),
                "active": backend == self.active_backend,
            }
            for backend in self.backends
        ]

    def cleanup(self):
        """Flush the persistent cache and clean up all backends."""
        self.save_cache()
        for backend in self.backends:
            try:
                backend.cleanup()
            except Exception as e:
                print(f"Cleanup error for {backend.get_name()}: {e}")
