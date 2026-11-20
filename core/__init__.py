"""Pure processing core: no Django or UI imports allowed (ARCHITECTURE.md section 3).

Functions here operate on explicit safe paths, streams and typed data
structures and return results; callers own authorization, job boundaries
and persistence. Submodules (filesafety, naming, pdf, imaging, ocr,
matching, layout) are added by their work packages.
"""
