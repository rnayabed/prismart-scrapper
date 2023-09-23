# PrismaRT Scrapper

dirty. hastly written. not recommended for use. Written for personal use only. 

Has hardcoded values to work only with 1200x2000 resolution. 

Contributions welcomed.

## Prerequisite

- adb connect device with PrismaRT open > Standard Dispense > Colour Pallete Search > Select Colour Pallete
- tesseract OCR in path
- requirements.txt
- PostgreSQL database

## Usage:

```
pip install -r requirements.txt
./scrapper.py <username> <password> <db name> <db location>
```

## License

[GNU General Public License v3.0](https://github.com/rnayabed/prismart-scrapper/blob/master/LICENSE)