from nemo.collections.asr.models import EncDecRNNTBPEModel


def main():
    models = EncDecRNNTBPEModel.list_available_models()
    print("All available NeMo ASR RNNT/Conformer-Transducer models containing 'transducer' or 'rnnt':\n")
    found = False
    for m in models:
        name = str(m)
        if "transducer" in name.lower() or "rnnt" in name.lower():
            print(name)
            found = True
    if not found:
        print("(none matching 'transducer' or 'rnnt' found)")


if __name__ == "__main__":
    main()
