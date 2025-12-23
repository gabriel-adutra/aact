import time
import os

def main():
    print("ETL Container Started...")
    print("Environment Variables Check:")
    print(f"AACT_HOST: {os.getenv('AACT_HOST')}")
    print(f"NEO4J_URI: {os.getenv('NEO4J_URI')}")
    
    # Keep alive for inspection
    print("Waiting...")
    time.sleep(10) 
    print("Done.")

if __name__ == "__main__":
    main()

