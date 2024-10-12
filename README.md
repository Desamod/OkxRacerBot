[![Static Badge](https://img.shields.io/badge/Telegram-Bot%20Link-Link?style=for-the-badge&logo=Telegram&logoColor=white&logoSize=auto&color=blue)](https://t.me/OKX_official_bot/OKX_Racer?startapp=linkCode_134115058)

## Recommendation before use

# 🔥🔥 Use PYTHON 3.10 🔥🔥

> 🇷 🇺 README in russian available [here](README-RU.md)

## Features  
| Feature                          | Supported |
|----------------------------------|:---------:|
| Multithreading                   |     ✅     |
| Proxy binding to session         |     ✅     |
| Support for  pyrogram .session   |     ✅     |
| Auto-farming                     |     ✅     |
| Auto-tasks (except KYC)          |     ✅     |
| Auto-boost                       |     ✅     |
| Auto-daily                       |     ✅     |


## [Settings](https://github.com/Desamod/OkxRacerBot/blob/master/.env-example/)
| Settings                |                                 Description                                 |
|-------------------------|:---------------------------------------------------------------------------:|
| **API_ID / API_HASH**   | Platform data from which to run the Telegram session (by default - android) |
| **SLEEP_TIME**          |             Sleep time between cycles (by default - [300, 500])             |
| **AUTO_BOOST**          |                     Buying a boost (by default - True)                      |
| **BOOSTERS**            |              Types of boost to buy (for all by default - True)              |
| **AUTO_TASK**           |                Auto tasks (except KYC task) (default - True)                |
| **REF_ID**              |                                Referral link                                |
| **RANDOM_PREDICTION**   |                Using random for prediction (default - True)                 |
| **MAX_COMBO_COUNT**     |                       Max combo count (default - 28)                        |
| **USE_PROXY_FROM_FILE** | Whether to use a proxy from the bot/config/proxies.txt file (True / False)  |

## Quick Start 📚

To fast install libraries and run bot - open run.bat on Windows or run.sh on Linux

## Prerequisites
Before you begin, make sure you have the following installed:
- [Python](https://www.python.org/downloads/) **version 3.10**

## Obtaining API Keys
1. Go to my.telegram.org and log in using your phone number.
2. Select "API development tools" and fill out the form to register a new application.
3. Record the API_ID and API_HASH provided after registering your application in the .env file.

## Installation
You can download the [**repository**](https://github.com/Desamod/OkxRacerBot) by cloning it to your system and installing the necessary dependencies:
```shell
git https://github.com/Desamod/OkxRacerBot
cd OkxRacerBot
```

Then you can do automatic installation by typing:

Windows:
```shell
run.bat
```

Linux:
```shell
run.sh
```

# Linux manual installation
```shell
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
cp .env-example .env
nano .env  # Here you must specify your API_ID and API_HASH, the rest is taken by default
python3 main.py
```

You can also use arguments for quick start, for example:
```shell
~/OkxRacerBot >>> python3 main.py --action (1/2)
# Or
~/OkxRacerBot >>> python3 main.py -a (1/2)

# 1 - Run clicker
# 2 - Creates a session
```

# Windows manual installation
```shell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env-example .env
# Here you must specify your API_ID and API_HASH, the rest is taken by default
python main.py
```

You can also use arguments for quick start, for example:
```shell
~/OkxRacerBot >>> python main.py --action (1/2)
# Or
~/OkxRacerBot >>> python main.py -a (1/2)

# 1 - Run clicker
# 2 - Creates a session
```

### Contacts

For support or questions, you can contact me

[![Static Badge](https://img.shields.io/badge/Telegram-Channel-Link?style=for-the-badge&logo=Telegram&logoColor=white&logoSize=auto&color=blue)](https://t.me/desforge_cryptwo)

