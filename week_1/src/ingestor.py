import email
import quopri
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
                        print(f"✅ Extracted: {Path(input_dir).name}")
                        return True
            print(f"⚠️ No HTML content found in: {input_dir}")
            return False
    except FileNotFoundError:
        print(f"File: {input_dir} not found")
        return False

def ingest_all_mhtml(input_dir, output_dir):
    failed = 0
    passed = 0
    cwd = Path.cwd()
    FullInputDir = cwd / input_dir
    FullOutputDir = cwd / output_dir

    try:
        InputDirList = [item for item in Path(FullInputDir).iterdir() if item.is_file()]
    except FileNotFoundError:
        print(f"Directory not found: {FullInputDir}")
        return
    if len(InputDirList) <= 0:
        print(f"Empty dir: {FullInputDir}")
        return False

    Path(FullOutputDir).mkdir(exist_ok=True)
    if Path(input_dir).is_dir:
        pass
    else:
        print(f"Invalid Directory: {input_dir}")

    print("🥉 Bronze")
    for file in InputDirList:
        FullInfileDir = FullInputDir / file
        FullOutfileDir = FullOutputDir / file.name
        outfile = str(FullOutfileDir).replace(".mhtml", ".html")
        if ingest_proccess(FullInfileDir, outfile):
            failed += 1
        else:
            passed += 1
    print("📊 Bronze Summary:")
    print(f"Total: {passed + failed} | Extracted: {passed} | Failed: {failed}\n")
