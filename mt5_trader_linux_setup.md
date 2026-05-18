Here is a clean **reusable Markdown setup file** you can save as:

```text
mt5_wine_setup_guide.md
```

It includes everything we fixed in your session so you can rebuild this system anytime.

---

````markdown
# MT5 + Wine + Linux Python Bridge Setup Guide (mt5linux)

This guide sets up a stable connection between:

- Kali Linux Python (bot)
- Wine Python
- MetaTrader 5 terminal
- mt5linux RPC bridge

---

# 1. Install system dependencies (Linux)

```bash
sudo dpkg --add-architecture i386
sudo apt update

sudo apt install wine64 wine32 winbind cabextract winetricks -y
sudo apt install libvulkan1 libvulkan1:i386 -y
````

---

# 2. Create Wine prefix for MT5

```bash
export WINEPREFIX=/home/$USER/.mt5
wineboot
```

Wait until initialization completes.

---

# 3. Install MetaTrader 5 in Wine

Download MT5:

[https://www.metatrader5.com/en/download](https://www.metatrader5.com/en/download)

Then install:

```bash
WINEPREFIX=/home/$USER/.mt5 wine terminal64.exe
```

Log in once and close MT5.

---

# 4. Install Visual C++ runtime (IMPORTANT FIX)

```bash
WINEPREFIX=/home/$USER/.mt5 winetricks vcrun2022
```

---

# 5. Install Python (USE 3.12 ONLY)

Download:

[https://www.python.org/downloads/release/python-3123/](https://www.python.org/downloads/release/python-3123/)

Install inside Wine:

```bash
WINEPREFIX=/home/$USER/.mt5 wine python-3.12.3-amd64.exe
```

During install:

✔ Add Python to PATH
✔ Install for all users

---

# 6. Verify Python

```bash
WINEPREFIX=/home/$USER/.mt5 wine python --version
```

---

# 7. Install required packages (CRITICAL FIXED VERSIONS)

```bash
WINEPREFIX=/home/$USER/.mt5 wine python -m pip install --upgrade pip

WINEPREFIX=/home/$USER/.mt5 wine python -m pip install MetaTrader5 rpyc mt5linux

# IMPORTANT: avoid numpy 2.x (Wine crash fix)
WINEPREFIX=/home/$USER/.mt5 wine python -m pip install numpy==1.26.4
```

---

# 8. Start MT5 terminal

```bash
 WINEPREFIX=/home/solace/.mt5 wine "/home/solace/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"

```

Keep it open and logged in.

---

# 9. Start mt5linux bridge server

```bash
WINEPREFIX=/home/$USER/.mt5 wine python -m mt5linux
```

Expected output:

```
server started on [127.0.0.1]:18812
```

Leave terminal running.

---

# 10. Verify bridge is listening

```bash
netstat -tulnp | grep 18812
```

Expected:

```
127.0.0.1:18812 LISTEN
```

---

# 11. Linux-side Python bot setup

Install dependencies in your Linux venv:

```bash
pip install mt5linux rpyc
```

---

# 12. Example bot connection code

```python
from mt5linux import MetaTrader5

mt5 = MetaTrader5()

MT5_PATH = "/home/$USER/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"

if not mt5.initialize(MT5_PATH):
    print("Initialization failed")
    exit()

print("Connected")

if mt5.login(ACCOUNT_ID, password=PASSWORD, server=SERVER):
    print("Login successful")
    print(mt5.account_info())

mt5.shutdown()
```

---

# 13. Correct startup order (VERY IMPORTANT)

Every time:

1. Start MT5 (Wine)
2. Start mt5linux bridge (Wine Python)
3. Run Linux bot (Kali Python)

---

# 14. Common errors & fixes

## ❌ Connection refused

* Bridge not running
* Wrong port (18812 default)

---

## ❌ ucrtbase.dll.crealf crash

Fix:

```bash
pip install numpy==1.26.4
```

---

## ❌ python.exe crash (Wine)

Fix:

```bash
winetricks vcrun2022
```

---

## ❌ Wrong Python version

Use ONLY:

```
Python 3.12.x
```

NOT 3.13 or 3.14

---

# 15. Architecture summary

```
Linux Bot (Kali Python)
        ↓
mt5linux (RPC bridge)
        ↓
Wine Python 3.12
        ↓
MetaTrader 5 terminal
```

---

# Done

This setup is now stable for:

* Trading bots
* CRT strategies
* Multi-timeframe execution
* OANDA/MT5 hybrid systems

```

---

If you want next upgrade, I can help you build:

- :contentReference[oaicite:0]{index=0}
- :contentReference[oaicite:1]{index=1}
- :contentReference[oaicite:2]{index=2}
- :contentReference[oaicite:3]{index=3}
- :contentReference[oaicite:4]{index=4}

Just say 👍
```
