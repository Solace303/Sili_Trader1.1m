import sys
# 1. Modify this line to instantiate the class object
from mt5linux import MetaTrader5
mt5 = MetaTrader5() 

# --- CONFIGURATION PARAMETERS ---
MT5_PATH = "/home/solace/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"

DEMO_ACCOUNT_ID = 107126058       
DEMO_PASSWORD = "@1OuNcEf"  
DEMO_SERVER = "MetaQuotes-Demo"   
#RO-password: U-HwM4Ul
# --------------------------------

print("Attempting to bridge Kali Linux native Python to Wine MT5...")

# 2. Pass the path directly as a positional argument (remove 'path=')
if not mt5.initialize(MT5_PATH):
    print("[-] Initialization Failed!")
    sys.exit()

print("[+] Native bridge established successfully!")

# 2. Attempt authentication with your Exness Demo credentials
login_success = mt5.login(DEMO_ACCOUNT_ID, password=DEMO_PASSWORD, server=DEMO_SERVER)

if login_success:
    print("[+] Login Successful! Your Python script is communicating with Exness.")
    
    # 3. Pull account information to verify read permissions
    account_info = mt5.account_info()
    if account_info is not None:
        print("\n--- ACCOUNT METRICS ---")
        print(f"Account Number: {account_info.login}")
        print(f"Broker Server:  {account_info.server}")
        print(f"Equity Balance: ${account_info.equity:.2f} {account_info.currency}")
        print(f"Account Leverage: 1:{account_info.leverage}")
    else:
        print("[-] Connected, but failed to fetch account info properties.")
        
else:
    print(f"[-] Login Failed. Server rejected credentials.")
    print(f"Error Code: {mt5.last_error()}")

# 4. Clean up the socket connection ports
print("\nClosing connection bridge gracefully...")
mt5.shutdown()
