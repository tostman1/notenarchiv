"""Original deterministic demo PDFs; normal ingestion still requires human approval."""

import argparse
from pathlib import Path


def pdf(title, part):
    # Minimal original vector drawing, not a transcription of any musical work.
    content = f"BT /F1 18 Tf 40 790 Td (SYNTHETIC TEST ONLY - {title}) Tj 0 -30 Td ({part}) Tj ET\n"
    for y in range(500, 600, 20):
        content += f"40 {y} m 550 {y} l S\n"
    content += "100 540 8 5 re f 108 540 m 108 590 l S\n"
    paired = title == "Testmarsch Alpha"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>" if paired else b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.276 841.89] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content.encode('ascii'))} >>\nstream\n{content}endstream".encode("ascii"),
    ]
    if paired:
        objects.append(objects[2])
    data, offsets = b"%PDF-1.4\n", [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    start = len(data)
    data += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:])
    return data + f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()


def create(root):
    root = Path(root)
    root.mkdir(exist_ok=False)
    for title in ("Testmarsch Alpha", "Testpolka Beta", "Testwalzer Gamma"):
        folder = root / title
        folder.mkdir()
        for part in ("Posaune 1", "Posaune 2"):
            with (folder / f"{part}.pdf").open("xb") as stream:
                stream.write(pdf(title, part))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    create(parser.parse_args().output)
