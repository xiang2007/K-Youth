import email
import os
from bs4 import BeautifulSoup
from email.message import EmailMessage

def ingest_proccess():
    #     res = ""
    # with open("/home/wee/Desktop/K-Youth/week_1/data/AI & Workflow Automation Associate Job in Kuala Lumpur - Jobstreet.mhtml", "rb", ) as file:
    #     msg = email.message_from_binary_file(file, policy=default)
    # decoded_string = ""
    # for part in msg.walk():
    #     if part.get_content_type() == "text/html":
    #         msg = part.get_content()
    #         break
	return

def ingest_all_html(input_dir, output_dir):
    curr_dir = os.getcwd()
    working_dir = input_dir
    os.chdir("../")
    data_dir = os.path.join(curr_dir, working_dir)
    dir_list = os.listdir(data_dir)