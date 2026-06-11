import email
import logging

from pathlib import Path

def ingest_proccess(input_dir, output_dir):
    try:
        with open(input_dir, "rb") as file:
            msg = email.message_from_binary_file(file)
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    with open(output_dir, "w", encoding="utf-8") as of:
                        payload = part.get_payload(decode=True)
                        if payload is not None:
                            of.write(payload.decode("utf-8", errors="ignore"))
                        logging.info(f"✅ Extracted: {Path(input_dir).name}")
                        return True
            logging.error(f"⚠️ No HTML content found in: {input_dir}")
            return False
    except FileNotFoundError:
        logging.error(f"File: {input_dir} not found")
        return False

def ingest_all_mhtml(input_dir, output_dir):
    failed = 0
    passed = 0
    FullInputDir = Path(input_dir).resolve()
    FullOutputDir = Path(output_dir).resolve()

    try:
        InputDirList = Path(FullInputDir).glob("*.mhtml")
    except FileNotFoundError:
        logging.error(f"Directory not found: {input_dir}")
        return

    if Path(input_dir).is_dir:
        pass
    else:
        logging.error(f"Invalid Directory: {input_dir}")
    Path(FullOutputDir).mkdir(exist_ok=True)

    print("🥉 Bronze")
    for file in InputDirList:
        FullInfileDir = FullInputDir / file
        FullOutfileDir = FullOutputDir / file.name
        outfile = str(FullOutfileDir).replace(".mhtml", ".html")
        if ingest_proccess(FullInfileDir, outfile):
            failed += 1
        else:
            passed += 1
    print("\n📊 Bronze Summary:")
    print(f"Total: {passed + failed} | Extracted: {passed} | Failed: {failed}\n")
