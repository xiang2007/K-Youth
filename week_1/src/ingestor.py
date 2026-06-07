import email
import os
import quopri
from bs4 import BeautifulSoup
from email import policy
from email.message import EmailMessage

def ingest_proccess(input_dir, output_dir):
    success = 0
    failed = 0
    input_list = os.listdir(input_dir)

    for f in input_list:
        with open(f, "rb") as file:
            msg = email.message_from_binary_file(file)
            for part in msg.walk():
                if part.get_content_type == "text/html":
                    outfile = f.replace(".mhtml", ".html")
                    with open(outfile, "w", encoding="utf-8") as of:
                        payload = part.get_payload(decode=True)
                        of.write((quopri.decodestring(payload)).decode('utf-8'))
                        return True
                return False



def inegst_all_mhtml(input_dir, output_dir):
    cwd = os.getcwd()
    FullInputDir = os.path.join(cwd, input_dir)
    FullOutputDir = os.path.join(cwd, output_dir)

    os.makedirs(FullOutputDir, exist_ok=True)
    if os.path.exists(input_dir):
        pass
    else:
        print(f"Invalid Directory: {input_dir}")
    





# def ingest_proccess(input_list, input_dir, out_dir):
#     res = ""
#     res_pass = 0
#     res_fail = 0
#     i = 0
#     for infile in input_list:
#         infile_dir = os.path.join(input_dir, infile)
#         try:
#             with open(infile_dir, "rb", ) as file:
#                 msg = email.message_from_binary_file(file, policy=policy.default)
#         except PermissionError:
#             res_fail += 1
#             continue
#         decoded_string = ""
#         flag = False
#         for part in msg.walk():
#             if part.get_content_type() == "text/html":
#                 res = part.get_content()
#                 res_pass += 1
#                 flag = True
#                 break
#         if flag is False:
#             res_fail += 1
#             print(f"⚠️ No HTML content found in {infile}")
#             continue
#         outfile = infile.replace("mhtml", "html") if ".mhtml" in infile else infile + ".html"
#         outdir = os.path.join(out_dir, outfile)
#         with open(outdir, "w", encoding="utf-8") as f:
#             f.write(res)
#             i += 1
#             print (f"✅ Extracted {outfile}")
#     print("📊 Bronze Summary:")
#     print(f"Total: {i} | Extracted: {res_pass} | Failed: {res_fail}")
#     return

# def ingest_all_html(input_dir):
#     curr_dir = os.getcwd()
#     working_dir = input_dir
#     data_dir = os.path.join(curr_dir, working_dir)
#     if os.path.exists(data_dir):
#         pass
#     else:
#         return {"NoDir": 1}
#     dir_list = os.listdir(data_dir)
#     res_list = []
#     for file in dir_list:
#         file_name, file_ext = os.path.splitext(file)
#         if file_ext != ".mhtml":
#             print(f"⚠️ Invalid file: {file}, not a mhtml file")
#             continue
#         else:
#             res_list.append(file)
#     try:
#         dest_dir = os.mkdir(os.path.join(curr_dir, "data/1_bronze"))
#     except FileExistsError:
#         dest_dir = os.path.join(curr_dir, "data/1_bronze")
#     return {"in_dir": working_dir, "res_list": res_list, "dest_dir": dest_dir, "NoDir": 0}

# def ingest():
#     res_list = ingest_all_html("data/0_source")
#     lst = [str]
#     dest = ""
#     if (res_list["NoDir"]):
#         return
#     else:
#         lst = res_list["res_list"]
#         dest = res_list["dest_dir"]
#     ingest_proccess(lst, res_list["in_dir"], dest)