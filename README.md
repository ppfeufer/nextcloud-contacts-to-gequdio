# Convert Nextcloud Contacts to GEQUDIO XML

This script converts contacts exported from Nextcloud in vCard format to GEQUDIO XML format, which can be imported into GEQUDIO phones.

______________________________________________________________________

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=2 -->

- [Installation and Usage](#installation-and-usage)
- [Importing Contacts to Your Gequdio Phone](#importing-contacts-to-your-gequdio-phone)

<!-- mdformat-toc end -->

______________________________________________________________________

## Installation and Usage<a name="installation-and-usage"></a>

- Clone this repository via Git:
  ```bash
  git clone https://github.com/ppfeufer/nextcloud-contacts-to-gequdio.git
  ```
- Ensure you have Python 3.x installed on your system.
- Create a virtual environment and activate it:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- Install the required `requests` library using pip:
  ```bash
  pip install -r requirements.txt
  ```
- Copy the settings file and modify it with your details:
  ```bash
  cp settings.ini.example settings.ini
  ```
  - `url`: The URL of your Nextcloud instance.
  - `username`: Your Nextcloud username.
  - `password`: Your Nextcloud password.
  - `addressbook`: The name of the address book to export contacts from. (Default is "contacts")
- Run the script:
  ```bash
  python3 nextcloud_contacts_to_gequdio.py
  ```
- Create a cron job to run the script periodically if desired.
  ```bash
  crontab -e
  ```
  Add the following line to run the script every day at midnight (Change the cron schedule as desired):
  ```cron
  0 0 * * * /path/to/your/venv/bin/python /path/to/nextcloud-contacts-to-gequdio/nextcloud_contacts_to_gequdio.py
  ```

The cron job will execute the script at the specified intervals, creating or updating the `gequdio.xml` file with the latest contacts from Nextcloud.
It is up to you to ensure that your GEQUDIO phone fetches the updated `gequdio.xml` file as needed. This may involve hosting the file on a web server or using another method to make it accessible to your phone.

## Importing Contacts to Your Gequdio Phone<a name="importing-contacts-to-your-gequdio-phone"></a>

- Import the generated `gequdio.xml` file into your GEQUDIO phone as per its instructions.
- Enjoy your synchronized contacts!
