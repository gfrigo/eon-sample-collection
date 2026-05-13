def encontrar_pendrive() -> Path | None:
    """
    Procura um pen drive gravável em /media/<user>/* ou /mnt/*.
    Retorna o primeiro diretório utilizável ou None.
    """
    candidatos = []
    for base in ("/media", "/mnt"):
        base_path = Path(base)
        if not base_path.exists():
            continue
        for item in base_path.iterdir():
            if not item.is_dir():
                continue
            if base == "/media":
                # /media/<usuario>/<label>
                for sub in item.iterdir():
                    if sub.is_dir() and os.access(sub, os.W_OK):
                        candidatos.append(sub)
            else:
                if os.access(item, os.W_OK):
                    candidatos.append(item)
    return candidatos[0] if candidatos else None


def diretorio_de_saida() -> tuple[Path, bool]:
    """Retorna (diretório, é_pendrive?)."""
    pendrive = encontrar_pendrive()
    if pendrive:
        out = pendrive / PHOTOS_SUBDIR
        out.mkdir(exist_ok=True)
        return out, True
    FALLBACK_PHOTO_DIR.mkdir(exist_ok=True)
    return FALLBACK_PHOTO_DIR, False