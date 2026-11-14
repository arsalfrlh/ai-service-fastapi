# pip install -U ctranslate2 sentencepiece huggingface_hub
from pathlib import Path

import ctranslate2
import sentencepiece as spm


class LocalTranslator:

    def __init__(
        self,
        model_path: str = r"E:\model\nmt\madlad400", #memuat model 
        device: str = "cpu" #menjalankan model dgn cpu
    ):
        self.model_path = Path(model_path) #menyimpan lokasi model di variabel

        # Validate model directory
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model directory not found: {self.model_path}"
            )

        required_files = [
            "model.bin", #Bobot neural network
            "config.json", #Konfigurasi arsitektur model
            "shared_vocabulary.json", #Vocabulary yang digunakan model
            "spiece.model" #Model tokenizer SentencePiece
        ]

        for filename in required_files: #memeriksa setiap file
            file_path = self.model_path / filename

            if not file_path.exists():
                raise FileNotFoundError(
                    f"Missing model file: {file_path}"
                )

        print("Loading SentencePiece tokenizer...")

        # Load SentencePiece tokenizer
        self.tokenizer = spm.SentencePieceProcessor() #Kita membuat objek tokenizer

        loaded = self.tokenizer.load( #Kita memuat vocabulary dan konfigurasi tokenisasi dari file spiece.model
            str(self.model_path / "spiece.model")
        )
        # Kenapa tokenizer perlu dimuat?
        # Karena neural network tidak memahami teks seperti manusia.
        # Model bekerja menggunakan representasi token numerik atau ID token. SentencePiece menyediakan cara untuk mengubah teks menjadi token dan sebaliknya.

        if not loaded:
            raise RuntimeError("Failed to load tokenizer")

        print("Loading MADLAD-400 model...")

        # Load CTranslate2 model
        self.translator = ctranslate2.Translator( #Memuat model MADLAD-400 menggunakan CTranslate2
            str(self.model_path), #Lokasi model
            device=device, #device untuk menjalankan model
            compute_type="int8", #Compute Type menentukan tipe komputasi yang digunakan, NT8 menggunakan representasi 8-bit untuk operasi model yang didukung
            inter_threads=1, #Inter Threads, Mengatur jumlah worker yang dapat menjalankan pekerjaan inference secara paralel.
            intra_threads=4 #Intra Threads
        )

        print("MADLAD-400 successfully loaded!")

    def translate(
        self,
        text: str,
        target_language: str = "id"
    ) -> str:

        if not isinstance(text, str) or not text.strip(): #Validasi input
            raise ValueError("Text cannot be empty")

        if not target_language.isalnum(): #Memastikan kode bahasa terdiri dari karakter alfanumerik.
            raise ValueError("Invalid target language code")

        # Add MADLAD target language token
        input_text = ( #Menambahkan prefix bahasa tujuan
            f"<2{target_language}> {text.strip()}" #input_text = "<2id> Hello, how are you?"
        )
        #Model ini menggunakan token khusus untuk menentukan bahasa tujuan penerjemahan.

        # Convert text into SentencePiece tokens
        input_tokens = self.tokenizer.encode( #Melakukan tokenisasi
            input_text,
            out_type=str
        )
        # Misal: <2id> Hello, how are you?
        # [
        #     "<2id>",
        #     "▁Hello",
        #     ",",
        #     "▁how",
        #     "▁are",
        #     "▁you",
        #     "?"
        # ]
        # Hasil sebenarnya bergantung pada tokenizer. Perhatikan ini out_type=str
        # Artinya kita meminta hasil token berupa string, bukan integer token ID.

        # Run local AI inference
        results = self.translator.translate_batch( #Menjalankan inference menggunakan CTranslate2
            [input_tokens], #Input, CTranslate2 menerima sekumpulan token sebagai batch.
            batch_type="tokens", #Batch type, Memberitahukan bahwa pengelompokan batch berdasarkan jumlah token, bukan jumlah contoh.
            beam_size=1, #Beam size, Menggunakan satu jalur kandidat saat proses decoding
            max_decoding_length=256 #Maximum decoding length, Membatasi panjang maksimum hasil generasi menjadi 256 token.
        )

        # Get generated tokens
        output_tokens = results[0].hypotheses[0] #Mengambil hasil inference
        # results
        # └── results[0]                #results[0]: hasil untuk input pertama.
        #         └── hypotheses        #hypotheses: kandidat hasil terjemahan.
        #             └── hypotheses[0] #hypotheses[0]: kandidat terjemahan pertama.
        #itulah alasan pakai input list [input_tokens]

        # Convert tokens back into text
        translated_text = self.tokenizer.decode( #Mengubah token kembali menjadi teks
            output_tokens
        )
        #Sebelumnya: Teks → Token | Sekarang: Token → Teks
        # Token String
        # [
        #     "▁Halo",
        #     ",",
        #     "▁apa",
        #     "▁kabar",
        #     "?"
        # ]
        # Text: Halo, apa kabar?

        return translated_text.strip()
        # Mengembalikan hasil terjemahan dan menghapus spasi di awal maupun akhir.

# Input Text: Hello, how are you?
# SentencePiece Tokenizer: Mengubah teks menjadi token
# CTranslate2: Menjalankan neural network MADLAD-400
# SentencePiece Decoder: Mengubah token kembali menjadi teks
# Output Text: Halo, apa kabar?

# CTranslate2 bukan model AI. Ia merupakan engine yang melakukan komputasi neural network menggunakan bobot model yang sudah dilatih.
# Analoginya:
# - MADLAD-400 adalah otaknya.
# - CTranslate2 adalah mesin yang menjalankan otak tersebut.
# - Python adalah aplikasi yang mengendalikan prosesnya.

# SentencePiece
# Digunakan untuk melakukan tokenisasi dan detokenisasi.
# Hello, how are you?
#           ↓
# ["▁Hello", ",", "▁how", "▁are", "▁you", "?"]