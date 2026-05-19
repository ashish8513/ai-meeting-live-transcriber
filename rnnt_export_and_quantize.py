import os

# Ensure PyTorch uses the legacy ONNX exporter which is compatible with
# NeMo's use of dynamic_axes.
os.environ.setdefault("TORCH_ONNX_EXPORTER_MODE", "deprecated")

import torch
from nemo.collections.asr.models import EncDecRNNTBPEModel
from onnxruntime.quantization import QuantType, quantize_dynamic


def export_rnnt_onnx(model_name: str = "stt_en_conformer_transducer_small",
                     fp32_onnx_path: str = "rnnt_conformer_small.onnx") -> None:
    """Load NeMo RNNT model and export to a single ONNX graph (CPU friendly).

    This uses the built-in NeMo export helper. Some NeMo versions also support
    exporting separate encoder/decoder/joint models, but for now we keep it
    simple and export a single ONNX file suitable for ONNX Runtime.
    """
    print(f"Loading NeMo RNNT model: {model_name} ...")
    model = EncDecRNNTBPEModel.from_pretrained(model_name=model_name)

    # Force CPU for export
    model = model.to("cpu")
    model.eval()
    model.freeze()

    print(f"Exporting to ONNX: {fp32_onnx_path} ...")
    # NeMo 2.x export API keeps a simple signature
    model.export(fp32_onnx_path)
    print("Export completed.")


def quantize_to_int8(fp32_onnx_path: str = "rnnt_conformer_small.onnx",
                     int8_onnx_path: str = "rnnt_conformer_small_int8.onnx") -> None:
    """Apply dynamic INT8 quantization to the ONNX model for fast CPU inference."""
    print(f"Quantizing ONNX model to INT8: {fp32_onnx_path} -> {int8_onnx_path} ...")
    quantize_dynamic(
        model_input=fp32_onnx_path,
        model_output=int8_onnx_path,
        per_channel=True,
        reduce_range=False,
        weight_type=QuantType.QInt8,
        op_types_to_quantize=["MatMul", "Gemm"],
    )
    print("INT8 quantization completed.")


if __name__ == "__main__":
    # Allow overriding paths via env vars if needed later
    fp32_path = os.getenv("RNNT_ONNX_FP32", "rnnt_conformer_small.onnx")
    int8_path = os.getenv("RNNT_ONNX_INT8", "rnnt_conformer_small_int8.onnx")

    export_rnnt_onnx(fp32_onnx_path=fp32_path)
    # NeMo exports separate encoder / decoder_joint graphs; quantize those.
    encoder_fp32 = "encoder-rnnt_conformer_small.onnx"
    encoder_int8 = "encoder-rnnt_conformer_small_int8.onnx"
    decoder_fp32 = "decoder_joint-rnnt_conformer_small.onnx"
    decoder_int8 = "decoder_joint-rnnt_conformer_small_int8.onnx"

    if os.path.exists(encoder_fp32):
        quantize_to_int8(fp32_onnx_path=encoder_fp32, int8_onnx_path=encoder_int8)
    if os.path.exists(decoder_fp32):
        quantize_to_int8(fp32_onnx_path=decoder_fp32, int8_onnx_path=decoder_int8)

    print("All done.")
