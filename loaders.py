"""
Amazon Selling Partner API (SP-API) - Chargement de données
────────────────────────────────────────────────────────────

Import de SKUs depuis les exports Seller Central.
Accepte un fichier ou un dossier (fusionne et déduplique).
"""

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _parse_single_export(filepath: Path) -> dict[str, str]:
    """Parse un seul fichier export Seller Central."""
    content = filepath.read_text(encoding="utf-8-sig")

    first_line = content.split("\n")[0]
    if "\t" in first_line:
        delimiter = "\t"
    elif ";" in first_line:
        delimiter = ";"
    else:
        delimiter = ","

    reader = csv.DictReader(content.splitlines(), delimiter=delimiter)
    skus: dict[str, str] = {}

    sku_keys  = ("seller-sku", "sku", "seller_sku", "Seller SKU", "SKU")
    asin_keys = ("asin1", "asin", "ASIN", "ASIN1", "product-id")

    for row in reader:
        sku  = ""
        asin = ""
        for k in sku_keys:
            if k in row and row[k].strip():
                sku = row[k].strip()
                break
        for k in asin_keys:
            if k in row and row[k].strip():
                asin = row[k].strip()
                break
        if sku:
            skus[sku] = asin

    return skus


def load_skus_from_seller_central_export(filepath: str) -> dict[str, str]:
    """
    Parse un ou plusieurs exports Seller Central pour en extraire les SKUs.
    
    Accepte :
      - Un chemin vers un fichier (.csv, .tsv, .txt)
      - Un chemin vers un DOSSIER → lit et fusionne tous les fichiers dedans
    
    Les SKUs sont dédupliqués automatiquement.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Chemin introuvable : {filepath}")

    all_skus: dict[str, str] = {}

    if path.is_dir():
        files = sorted(
            f for f in path.iterdir()
            if f.is_file() and f.suffix.lower() in (".csv", ".tsv", ".txt")
        )
        if not files:
            raise FileNotFoundError(f"Aucun fichier CSV/TSV/TXT dans : {filepath}")

        for f in files:
            try:
                skus = _parse_single_export(f)
                before = len(all_skus)
                all_skus.update(skus)
                new = len(all_skus) - before
                logger.info("  %s : %d SKUs (%d nouveaux)", f.name, len(skus), new)
            except Exception as e:
                logger.warning("  %s : erreur de lecture — %s", f.name, e)

        logger.info("Import dossier : %d SKUs uniques depuis %d fichiers", len(all_skus), len(files))
    else:
        all_skus = _parse_single_export(path)
        logger.info("Import CSV : %d SKUs chargés depuis %s", len(all_skus), path.name)

    return all_skus