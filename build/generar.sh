#!/bin/sh
# Regenera los tres PDF del TP5 (desde la carpeta TP5/)
set -e
uv run python build/build_docs.py docs/TP5_Desarrollo.md --caratula --indice
uv run python build/build_docs.py docs/TP5_Documento_Tecnico.md --indice
uv run python build/build_docs.py docs/TP5_Guia_Demostracion.md
