"""
Downloads and extracts XML archives from gesetze-im-internet.de.
Each law is distributed as a ZIP containing one XML file.
"""
import io
import logging
import zipfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Canonical URLs for supported laws
LAW_URLS: dict[str, str] = {
    # Prio 1 — Einkommensteuer-Kerngesetze
    "EStG":  "https://www.gesetze-im-internet.de/estg/xml.zip",
    "EStDV": "https://www.gesetze-im-internet.de/estdv_1955/xml.zip",
    "AO":    "https://www.gesetze-im-internet.de/ao_1977/xml.zip",
    "UStG":  "https://www.gesetze-im-internet.de/ustg_1980/xml.zip",
    # Prio 2 — Ergänzende Steuergesetze
    "SolzG":  "https://www.gesetze-im-internet.de/solzg_1995/xml.zip",
    "GewStG": "https://www.gesetze-im-internet.de/gewstg/xml.zip",
}


async def download_law_xml(law: str, dest_dir: Path) -> Path:
    """
    Download and extract the XML for *law* into *dest_dir*.
    Returns the path to the extracted XML file.
    Raises KeyError for unsupported law names.
    """
    url = LAW_URLS[law]
    dest_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading %s from %s", law, url)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        xml_files = [n for n in zf.namelist() if n.endswith(".xml")]
        if not xml_files:
            raise ValueError(f"No XML file found in ZIP for {law}")
        xml_name = xml_files[0]
        zf.extract(xml_name, dest_dir)
        logger.info("Extracted %s → %s/%s", law, dest_dir, xml_name)

    return dest_dir / xml_name
