"""扫描版教材批量 OCR 工具（离线中文识别，带逐页缓存）。

用法：
    python scripts/ocr_pdf.py <pdf路径> <起页> <止页> <输出txt> [--dpi 200]

页码为 1 起算的 PDF 物理页码（含封面、前言等）。识别结果按页写入缓存目录
instance/ocr_cache/<书名hash>/pNNNN.txt，重复运行不会重复识别。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

import numpy as np
import pymupdf
from rapidocr_onnxruntime import RapidOCR

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
CACHE_ROOT = os.path.join(BASE, "instance", "ocr_cache")

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = RapidOCR()
    return _ocr


def page_cache_path(pdf_path: str, page_no: int, dpi: int) -> str:
    key = hashlib.md5(pdf_path.encode("utf-8")).hexdigest()[:12]
    folder = os.path.join(CACHE_ROOT, key)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"p{page_no:04d}_d{dpi}.txt")


def ocr_page(doc, page_no: int, dpi: int) -> str:
    cache = page_cache_path(doc.name, page_no, dpi)
    if os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return f.read()

    pix = doc[page_no - 1].get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    elif pix.n == 1:
        img = np.repeat(img, 3, axis=2)
    img = np.ascontiguousarray(img[:, :, ::-1])  # RGB -> BGR

    result, _ = get_ocr()(img)
    lines = []
    if result:
        # 按文本框中心 y 排序（保留同行顺序），去掉过低置信度的噪声
        items = [(box, txt, score) for box, txt, score in result if score >= 0.5]
        items.sort(key=lambda it: (min(p[1] for p in it[0]), min(p[0] for p in it[0])))
        lines = [it[1].strip() for it in items if it[1].strip()]

    text = "\n".join(lines)
    with open(cache, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("start", type=int)
    ap.add_argument("end", type=int)
    ap.add_argument("output")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    doc = pymupdf.open(args.pdf)
    chunks = []
    for pno in range(args.start, min(args.end, len(doc)) + 1):
        text = ocr_page(doc, pno, args.dpi)
        chunks.append(f"\n===== PDF页 {pno} =====\n{text}")
        print(f"[OCR] page {pno}: {len(text)} chars", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(chunks))
    print(f"[DONE] {args.output}")


if __name__ == "__main__":
    main()
