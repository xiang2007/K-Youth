from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError
from pathlib import Path
import logging

class JobListing(BaseModel):
    source_id : str = Field(min_length=1)
    job_title : str = Field(min_length=1)
    company : str = Field(min_length=1)
    description : str = Field(min_length=1)

def process_all_html(input_dir, output_dir):
    success = 0
    failed = 0
    FullInputDir = Path(input_dir).resolve()
    FullOutputDir = Path(output_dir).resolve()

    if not FullInputDir.is_dir():
        logging.error(f"Directory not found: {input_dir}")
        return

    FullOutputDir.mkdir(exist_ok=True)
    input_dir_list = [list for list in FullInputDir.iterdir()]
    print("🥈 Silver")

    for file in input_dir_list:
        FullInfile = FullInputDir / file
        FullOutfile = FullOutputDir / str(file.name).replace(".html", "json")
        if process_html(FullInfile, FullOutfile):
            success += 1
            logging.info(f"✅ Extracted: {Path(file).name}")
        else:
            failed += 1
    print("\n📊 Silver Summary:")
    print(f"Total: {success + failed} | Processed: {success} | Skipped: {failed}\n")


def process_html(input_dir, output_dir):
    input_dir = Path(input_dir)
    with open(input_dir, "r", encoding="utf-8") as infile:
        soup = BeautifulSoup(infile, 'html.parser')

    # Find title attribute and check does it have content inside
    raw_job_title = str(soup.find(attrs={"data-automation": "job-detail-title"}))
    job_title = BeautifulSoup(raw_job_title, "html.parser").get_text(separator=' ', strip=True)
    if job_title == 'None':
        job_title = ""

    # Get source id at end of link
    raw_source = soup.find(attrs={"data-rh": "true", "property" : "og:url"})
    if raw_source and raw_source.has_attr("content") and str(raw_source) != '':
        source_id = str(raw_source["content"]).split("/")[-1] # split the html and get the last item
    else:
        source_id = ''

    # Get raw desc and convert into beautifulsoup class, then remove all the html attributes
    raw_desc = soup.find(attrs={"data-automation" : "jobAdDetails"})
    desc = BeautifulSoup(str(raw_desc), "html.parser").get_text(separator=' ', strip=True)
    if desc == "None":
        desc = ''

    raw_company_element = soup.find(attrs={"data-automation": "advertiser-name"})
    if raw_company_element:
        company_name = BeautifulSoup(str(raw_company_element), "html.parser").get_text(separator=" ", strip=True)
    else:
        company_name = ''

    try:
        j = JobListing(
            source_id=source_id,
            job_title=job_title,
            company=company_name,
            description=desc
        )
    except ValidationError as e:
        for error in e.errors():
            logging.warning(f"⚠️ Failed to process: {str(error['loc'][0])} | Reason: %s {input_dir.name}")
        return False

    with open(output_dir, 'w', encoding='utf-8') as outfile:
        outfile.write(j.model_dump_json(indent=4))
    return True