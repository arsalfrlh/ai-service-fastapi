from app.core.config import MODEL_PATH, DEVICE, COMPUTE_TYPE, INTER_THREADS, INTRA_THREADS
from pathlib import Path
import ctranslate2
import sentencepiece as spm

class TranslatorService:
    def __init__(self):
        self.translator: ctranslate2.Translator | None = None
        self.tokenizer: spm.SentencePieceProcessor | None = None
        self.model_path = Path(MODEL_PATH)

    def load_model(self):
        if self.translator is not None and self.tokenizer is not None:
            return
        if self.tokenizer is None:
            print("Load the tokenizer...")
            self.tokenizer = spm.SentencePieceProcessor()
            loaded =  self.tokenizer.load(model_file=str(self.model_path / "spiece.model"))
            if not loaded:
                print("Tokenizer failed to load")
                return
        if self.translator is None:
            print("Load the model...")
            if not self.model_path.exists():
                print("Model Path not exists")
                return

            self.translator = ctranslate2.Translator(
                str(self.model_path),
                device=DEVICE,
                compute_type=COMPUTE_TYPE,
                inter_threads=INTER_THREADS,
                intra_threads=INTRA_THREADS
            )
            print("Model loaded")

    def translate(self, word: str, target_language: str = "id"):
        if self.translator is None or self.tokenizer is None:
            self.load_model()
        if not isinstance(word, str) or not word.strip():
            raise ValueError("Text cannot be empty")
        if not target_language.isalnum():
            raise ValueError("Invalid target language code")

        input_text = f"<2{target_language}> {word.strip()}"
        input_token = self.tokenizer.encode(
            input=input_text,
            out_type=str
        )

        results = self.translator.translate_batch(
            [input_token],
            batch_type="tokens",
            beam_size=1,
            max_decoding_length=256
        )

        output_tokens = results[0].hypotheses[0]
        translated_text = self.tokenizer.decode(input=output_tokens)
        return translated_text.strip()

translator_service = TranslatorService()