"""Private protocol entry point. OS limits are already active before import."""

import json
import logging
import os
import sys
from pathlib import Path

from core.pdf.types import Limits, PdfError


class BoundedOutput:
    def __init__(self, stream, maximum):
        self.stream, self.maximum = stream, maximum

    def write(self, data):
        if self.stream.tell() + len(data) > self.maximum:
            raise PdfError("LIMIT_EXCEEDED")
        return self.stream.write(data)

    def tell(self):
        return self.stream.tell()

    def flush(self):
        return self.stream.flush()


def main(stage):
    os.umask(0o077)
    logging.disable(logging.CRITICAL)
    readers = []
    from pypdf import overwrite_configuration
    from pypdf.errors import LimitReachedError

    try:
        from core.pdf.structure import inspect, open_pdf

        request = json.loads((stage / "request.json").read_bytes())
        limits = Limits(**request["limits"])
        decoded = min(33_554_432, limits.memory_bytes // 8)
        overwrite_configuration(
            maximum_declared_stream_length=limits.max_bytes,
            array_based_stream_maximum_output_length=decoded,
            zlib_maximum_output_length=decoded,
            brotli_maximum_output_length=decoded,
            lzw_maximum_output_length=decoded,
            run_length_maximum_output_length=decoded,
            jbig2_maximum_output_length=decoded,
            image_maximum_buffer_size=decoded,
            stream_decoding_work_maximum_length=decoded * 4,
            page_tree_maximum_entries=limits.max_pages * 16,
            page_tree_maximum_page_entries=limits.max_pages * 100,
            page_tree_maximum_depth=64,
            jbig2dec_binary=None,
        )
        infos = []
        for index in range(request["inputs"]):
            reader, pages = open_pdf(stage / f"{index}.pdf", limits)
            readers.append(reader)
            infos.append(pages)
        if request["operation"] == "inspect":
            response = inspect(
                readers[0],
                infos[0],
                limits,
                request["include_text"],
                include_source_geometry=request.get("include_source_geometry", False),
            )
        else:
            metadata = {}
            with (stage / "output").open("xb") as raw:
                stream = BoundedOutput(raw, limits.max_output_bytes)
                if request["operation"] == "render":
                    from core.pdf.rendering import render

                    page = request["page"]
                    if page >= len(infos[0]):
                        raise PdfError("INVALID_PAGE")
                    annotations = readers[0].pages[page].get("/Annots", [])
                    if hasattr(annotations, "get_object"):
                        annotations = annotations.get_object()
                    form = readers[0].trailer["/Root"].get("/AcroForm")
                    if (form and form.get_object().get("/XFA")) or any(
                        item.get_object().get("/Subtype") == "/Widget" for item in annotations
                    ):
                        raise PdfError("UNSUPPORTED_ANNOTATION")
                    render(stage / "0.pdf", infos[0][page], request, limits, stream)
                elif request["operation"] == "merge":
                    from core.pdf.merging import merge

                    merge(readers, request["selections"], limits, stream)
                elif request["operation"] == "compose":
                    from core.pdf.composition import compose

                    metadata = {"origins": compose(readers, request, limits, stream)}
                elif request["operation"] == "print":
                    from core.pdf.printing import render

                    metadata = {"plan": render(readers[0], request["origins"], request["mode"], limits, stream)}
                else:
                    raise PdfError("INVALID_PDF")
            response = {"ok": True, **metadata}
    except PdfError as error:
        response = {"error": error.code}
    except MemoryError:
        response = {"error": "LIMIT_EXCEEDED"}
    except LimitReachedError:
        response = {"error": "LIMIT_EXCEEDED"}
    except Exception:
        response = {"error": "INVALID_PDF"}
    finally:
        for reader in readers:
            reader.close()
    (stage / "response.json").write_text(json.dumps(response, ensure_ascii=True), encoding="ascii")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
