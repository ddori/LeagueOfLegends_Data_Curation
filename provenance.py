import subprocess
from pathlib import Path
from datetime import datetime
import hashlib
import os
import prov.model as prov
from prov.dot import prov_to_dot


def run_unified(script_path: str = "unified.py"):
    """Execute the unified dataset builder."""
    subprocess.run(["python", script_path], check=True)


def sha256sum(file_path: str) -> str:
    """Return SHA256 hex digest for a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def add_file(doc: prov.ProvDocument, identifier: str, file_path: str):
    """
    Create a file entity given an identifier and path.
    If the file does not exist, mark it as missing instead of raising.
    """
    p = Path(file_path)
    attrs = [
        (prov.PROV_TYPE, "File"),
        ("ex:path", str(file_path)),
    ]

    if p.exists():
        size = p.stat().st_size
        digest = sha256sum(str(p))
        attrs.append(("ex:size_bytes", size))
        attrs.append(("ex:sha256", digest))
    else:
        attrs.append(("ex:missing", True))

    entity = doc.entity(identifier, attrs)
    return entity


def main():
    # ------------------------------------------------------------------
    # 1. Initialize PROV document and namespaces
    # ------------------------------------------------------------------
    doc = prov.ProvDocument()
    doc.add_namespace("ex", "https://example.org/terms/")

    agent = doc.agent(
        "ex:author_juhwan",
        (
            (prov.PROV_TYPE, "prov:Person"),
            ("ex:email", "juhwans3@illinois.edu"),
        ),
    )

    # Environment entity (e.g., container image or conda env)
    image_ref = os.environ.get("IMAGE_REF", "unknown")
    image_digest = os.environ.get("IMAGE_DIGEST", "unknown")

    environment = doc.entity(
        "ex:environment",
        (
            (prov.PROV_TYPE, "ex:Environment"),
            ("ex:image_ref", image_ref),
            ("ex:image_digest", image_digest),
        ),
    )

    # ------------------------------------------------------------------
    # 2. Run the unified.py script (analysis step)
    #    - SoloQ/pro cleaning/acquisition are assumed to be already done.
    # ------------------------------------------------------------------
    start_time = datetime.utcnow()
    run_unified("unified.py")
    end_time = datetime.utcnow()

    build_unified = doc.activity(
        "ex:build_unified_dataset",
        start_time,
        end_time,
        {prov.PROV_TYPE: "ex:Execution"},
    )

    doc.wasAssociatedWith(build_unified, agent)
    doc.used(build_unified, environment)

    # ------------------------------------------------------------------
    # 3. File entities (raw -> clean -> unified)
    #    Adjust paths if your repo layout differs.
    # ------------------------------------------------------------------
    # SoloQ files
    soloq_raw = add_file(doc, "ex:soloq_raw", "SoloQ/data/soloq_full_15.24.csv")
    soloq_clean = add_file(doc, "ex:soloq_clean", "SoloQ/data/soloq_clean_15.24.csv")
    soloq_clean_script = add_file(doc, "ex:soloq_clean_script", "SoloQ/clean.py")

    # Pro files
    pro_raw = add_file(
        doc,
        "ex:pro_raw",
        "pro/data/2025_LoL_esports_match_data_from_OraclesElixir.csv",
    )
    pro_clean = add_file(doc, "ex:pro_clean", "pro/data/pro_2025_cleaned.csv")
    pro_clean_script = add_file(doc, "ex:pro_clean_script", "pro/clean_pro_data.py")

    # Unified output
    unified_script = add_file(doc, "ex:unified_script", "unified.py")
    unified_output = add_file(
        doc,
        "ex:unified_dataset",
        "unified_pro_soloq_with_metrics.csv",
    )

    # ------------------------------------------------------------------
    # 4. Relations: how files and scripts are connected
    # ------------------------------------------------------------------
    # Cleaning activities (logical, even if they were run earlier)
    clean_soloq_act = doc.activity(
        "ex:clean_soloq",
        other_attributes={prov.PROV_TYPE: "ex:Cleaning"},
    )
    doc.wasAssociatedWith(clean_soloq_act, agent)
    doc.used(clean_soloq_act, soloq_raw)
    doc.used(clean_soloq_act, soloq_clean_script)
    doc.wasGeneratedBy(soloq_clean, clean_soloq_act)
    doc.wasDerivedFrom(soloq_clean, soloq_raw)

    clean_pro_act = doc.activity(
        "ex:clean_pro",
        other_attributes={prov.PROV_TYPE: "ex:Cleaning"},
    )
    doc.wasAssociatedWith(clean_pro_act, agent)
    doc.used(clean_pro_act, pro_raw)
    doc.used(clean_pro_act, pro_clean_script)
    doc.wasGeneratedBy(pro_clean, clean_pro_act)
    doc.wasDerivedFrom(pro_clean, pro_raw)

    # Unified build activity (actually executed above)
    doc.used(build_unified, soloq_clean)
    doc.used(build_unified, pro_clean)
    doc.used(build_unified, unified_script)
    doc.wasGeneratedBy(unified_output, build_unified)
    doc.wasDerivedFrom(unified_output, soloq_clean)
    doc.wasDerivedFrom(unified_output, pro_clean)

    # ------------------------------------------------------------------
    # 5. Serialize: PNG graph + JSON bundle
    # ------------------------------------------------------------------
    dot = prov_to_dot(doc)
    dot.write_png("provenance.png")

    doc.serialize("provenance.json", format="json")

    print("provenance.py completed successfully.")
    print("Generated:")
    print("- unified_pro_soloq_with_metrics.csv (via unified.py)")
    print("- provenance.json")
    print("- provenance.png")


if __name__ == "__main__":
    main()
