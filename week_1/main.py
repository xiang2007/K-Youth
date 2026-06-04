import email
import quopri
import os
from email.message import EmailMessage
from email.policy import default

def main():
    curr_dir = os.getcwd()
    subfolder = os.path.join(curr_dir, "data/0_source")
    print(subfolder)

if __name__ == "__main__":
    main()
