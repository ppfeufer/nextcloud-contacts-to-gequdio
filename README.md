# Convert Nextcloud Contacts to GEQUDIO XML

[![License](https://img.shields.io/github/license/ppfeufer/nextcloud-contacts-to-gequdio)](https://github.com/ppfeufer/nextcloud-contacts-to-gequdio/blob/master/LICENSE)
![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/ppfeufer/nextcloud-contacts-to-gequdio/master.svg)](https://results.pre-commit.ci/latest/github/ppfeufer/nextcloud-contacts-to-gequdio/master)
[![Code Style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](http://black.readthedocs.io/en/latest/)
[![Automated Checks](https://github.com/ppfeufer/nextcloud-contacts-to-gequdio/actions/workflows/automated-checks.yml/badge.svg)](https://github.com/ppfeufer/nextcloud-contacts-to-gequdio/actions/workflows/automated-checks.yml)
[![codecov](https://codecov.io/gh/ppfeufer/nextcloud-contacts-to-gequdio/graph/badge.svg?token=eDQz9UcBET)](https://codecov.io/gh/ppfeufer/nextcloud-contacts-to-gequdio)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/N4N8CL1BY)

This script converts contacts exported from Nextcloud in vCard format to GEQUDIO XML
format, which can be imported into GEQUDIO phones.

______________________________________________________________________

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=2 -->

- [Installation and Usage](#installation-and-usage)
- [Importing Contacts to Your Gequdio Phone](#importing-contacts-to-your-gequdio-phone)

<!-- mdformat-toc end -->

______________________________________________________________________

## Installation and Usage<a name="installation-and-usage"></a>

- Ensure you have Python 3.10 or higher installed on your system.
- Create a virtual environment and activate it:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- Install the package using pip:
  ```bash
  pip install nextcloud-contacts-to-gequdio==2.0.0
  ```
- Copy the settings file and modify it with your details:
  ```bash
  wget https://raw.githubusercontent.com/ppfeufer/nextcloud-contacts-to-gequdio/refs/heads/master/nextcloud_contacts_to_gequdio/settings.ini.example
  mv settings.ini.example settings.ini
  ```
  You should now have the following structure:
  ```
  .
  ├── venv
  └── settings.ini
  ```
- Edit the `settings.ini` file and fill in the required information:
  - `url`: The URL of your Nextcloud instance.
  - `username`: Your Nextcloud username.
  - `password`: Your Nextcloud password.
  - `addressbook`: The name of the address book to export contacts from. (Default is
    "contacts")
- Run the script:
  ```bash
  /path/to/your/venv/bin/nextcloud-contacts-to-gequdio
  ```
- Create a cron job to run the script periodically if desired.
  ```bash
  crontab -e
  ```
  Add the following line to run the script every day at midnight (Change the cron
  schedule as desired):
  ```cron
  0 0 * * * /path/to/your/venv/bin/nextcloud-contacts-to-gequdio
  ```

The cron job will execute the script at the specified intervals, creating or
updating the `gequdio.xml` (which can be found in the same directory as your venv
folder and settings file) file with the latest contacts from Nextcloud. It is up to
you to ensure that your GEQUDIO phone fetches the updated `gequdio.xml` file as
needed. This may involve hosting the file on a web server or using another method to
make it accessible to your phone.

## Importing Contacts to Your Gequdio Phone<a name="importing-contacts-to-your-gequdio-phone"></a>

- Import the generated `gequdio.xml` file into your GEQUDIO phone as per its instructions.
- Enjoy your synchronized contacts!
