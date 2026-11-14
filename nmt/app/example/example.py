
from translator import LocalTranslator


def main():

    print("=" * 50)
    print("MADLAD-400 LOCAL AI TRANSLATOR")
    print("=" * 50)

    # Load model once
    translator = LocalTranslator()

    print("\nTranslator is ready!")
    print("Type 'exit' to close the application.\n")

    while True:

        text = input("\nEnter text: ").strip()

        if text.lower() == "exit":
            print("Goodbye!")
            break

        if not text:
            print("Please enter some text.")
            continue

        target_language = input(
            "Target language (id/en/ja/ko): "
        ).strip().lower()

        if not target_language:
            target_language = "id"

        try:

            print("\nTranslating...")

            result = translator.translate(
                text=text,
                target_language=target_language
            )

            print("\nOriginal:")
            print(text)

            print("\nTranslation:")
            print(result)

        except Exception as error:
            print(f"\nTranslation failed: {error}")


if __name__ == "__main__":
    main()
