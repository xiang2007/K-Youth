from src.ingestor import ingest_all_mhtml

def main():
    ingest_all_mhtml("data/0_source", "data/1_bronze")
if __name__ == "__main__":
    main()
