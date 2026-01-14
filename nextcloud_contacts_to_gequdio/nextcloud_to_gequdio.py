"""
Nextcloud Contacts to GEQUDIO Contact XML Converter

This script connects to a Nextcloud instance via WebDAV, retrieves contacts from a specified addressbook,
and converts them into GEQUDIO-compatible contact XML format.

Requirements:
- requests

"""

# Standard Library
import configparser
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

# Third Party
import requests
from requests.auth import HTTPBasicAuth

# Nextcloud Contacts to GEQUDIO
from nextcloud_contacts_to_gequdio import __version__


def load_settings(path: str) -> dict:
    """
    Loads Nextcloud connection settings from an INI file.

    :param path: Path to the INI file.
    :type path: str
    :return: Dictionary with settings: url, username, password, addressbook, verify_ssl
    :rtype: dict
    """

    config = configparser.ConfigParser()
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Settings file not found: {path}")

    config.read(path)

    if "nextcloud" not in config:
        raise KeyError(f"Missing 'nextcloud' section in {path}")

    section = config["nextcloud"]

    # Set default addressbook if not provided
    addressbook = section.get("addressbook", fallback="contacts")
    if addressbook is None or not addressbook.strip():
        addressbook = "contacts"

    return {
        "url": section.get("url"),
        "username": section.get("user"),
        "password": section.get("password"),
        "addressbook": addressbook,
        "verify_ssl": section.getboolean("verify_ssl", True),
    }


class NextcloudWebDAVClient:
    """
    Minimal WebDAV client for Nextcloud Contacts.
    """

    def __init__(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        url: str,
        username: str,
        password: str,
        addressbook: str = "contacts",
        verify_ssl: bool = True,
    ):
        """
        Initializes the Nextcloud WebDAV client.

        :param url: Nextcloud base URL
        :type url: str
        :param username: Username
        :type username: str
        :param password: Password
        :type password: str
        :param addressbook: Address book name (default: "contacts")
        :type addressbook: str
        :param verify_ssl: Whether to verify SSL certificates
        :type verify_ssl: bool
        """

        self.base_url = urljoin(
            url.rstrip("/") + "/",
            f"remote.php/dav/addressbooks/users/{username}/{addressbook}/",
        )
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username=username, password=password)
        self.verify = verify_ssl

    @staticmethod
    def _get_user_agent() -> str:
        """
        Returns a default User-Agent string for HTTP requests.

        :return: User-Agent string
        :rtype: str
        """

        return (
            f"NextcloudContactsToGEQUDIO/{__version__} "
            f"(+https://github.com/ppfeufer/nextcloud-contacts-to-gequdio) via python-requests/{requests.__version__}"
        )

    @staticmethod
    def _parse_vcard(  # pylint: disable=too-many-locals, too-many-branches
        vcard: str,
    ) -> tuple[str, list[tuple[str, list[str]]]]:
        """
        Parses a vCard string to extract the full name and telephone numbers with types.

        :param vcard: vCard string
        :type vcard: str
        :return: Tuple of full name and list of (number, [types])
        :rtype: Tuple[str, List[Tuple[str, List[str]]]]
        """

        # Normalize line endings and split
        lines = vcard.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        # Unfold folded lines (lines that start with space or tab are continuations),
        # but if a continuation looks like a new property (e.g. "TEL;...:"), treat it as a separate line.
        unfolded = []
        prop_pattern = re.compile(r"^[A-Za-z0-9\-]+(?:;.*)?:")  # matches "PROP[:|;...]"

        for line in lines:
            if not line:
                continue

            if line[0] in (" ", "\t") and unfolded:
                cont = line[1:]

                if prop_pattern.match(cont):
                    # Continuation actually looks like a property -> add as new line
                    unfolded.append(cont)
                else:
                    # Decide whether to insert a space when unfolding based on the previous property
                    prev = unfolded[-1]
                    prev_key = prev.split(":", 1)[0]
                    prev_prop = prev_key.split(";", 1)[0].upper().strip()

                    if prev_prop == "TEL":
                        # Phone numbers should be concatenated without spaces
                        unfolded[-1] += cont
                    else:
                        # For textual properties (like FN) insert a space if appropriate
                        if not prev.endswith(" ") and not cont.startswith(" "):
                            unfolded[-1] += " " + cont
                        else:
                            unfolded[-1] += cont
            else:
                unfolded.append(line)

        name = "Unknown"
        numbers = []

        for line in unfolded:  # pylint: disable=too-many-nested-blocks
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            prop = key.split(";", 1)[0].upper().strip()

            if prop == "FN":
                name = value.strip() or "Unknown"
            elif prop == "TEL":
                val = value.strip()

                if not val:
                    # skip empty telephone values
                    continue

                types = []

                if ";" in key:
                    params = key.split(";")[1:]

                    for p in params:
                        if "=" in p:
                            k, v = p.split("=", 1)

                            if k.strip().upper() == "TYPE":
                                types.extend(
                                    [
                                        t.strip().lower()
                                        for t in v.split(",")
                                        if t.strip()
                                    ]
                                )
                        else:
                            if p.strip():
                                types.append(p.strip().lower())

                numbers.append((val, types))

        return name, numbers

    def download_all_contacts(self) -> list[str]:
        """
        Downloads all contacts as vCard strings.

        :return: List of vCard strings
        :rtype: List[str]
        """

        # Perform a single CardDAV REPORT to fetch all vCards in one request
        body = """<?xml version="1.0"?>
        <C:addressbook-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
            <D:prop>
                <D:getetag/>
                <C:address-data/>
            </D:prop>
            <C:filter/>
        </C:addressbook-query>
        """

        self.session.headers.update({"User-Agent": self._get_user_agent()})

        headers = {
            "Content-Type": 'application/xml; charset="utf-8"',
            "Depth": "1",
        }
        resp = self.session.request(
            method="REPORT",
            url=self.base_url,
            data=body.encode("utf-8"),
            headers=headers,
            verify=self.verify,
        )

        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        vcards = []

        for response in root.findall(".//{DAV:}response"):
            addrdata = response.find(".//{urn:ietf:params:xml:ns:carddav}address-data")

            if addrdata is not None and addrdata.text:
                vcards.append(addrdata.text)

        return vcards

    def create_gequdio_contact_xml(
        self, vcard_list: list[str], write_path: str | None = None
    ) -> str:
        """
        Creates GEQUDIO contact XML from a list of vCard strings.

        :param vcard_list: List of vCard strings
        :type vcard_list: List[str]
        :param write_path: Optional path to write the XML file
        :type write_path: Optional[str]
        :return: GEQUDIO contact XML string
        :rtype: str
        """

        root_node = ET.Element("GEQUDIODirectory")

        # Sort contacts by full name (case-insensitive) before processing
        for vcard in sorted(vcard_list, key=lambda v: self._parse_vcard(v)[0].lower()):
            contact_name, tels = self._parse_vcard(vcard)

            contact_node = ET.SubElement(root_node, "DirectoryEntry")
            ET.SubElement(contact_node, "Name").text = contact_name

            print(
                f"Processing contact: {contact_name} with {len(tels)} telephone entries."
            )

            for number, types in tels:
                tag = next(
                    (
                        group
                        for group, keywords in (
                            # GEQUDIO sees "Telephone" as "Office", so map accordingly here
                            ("Telephone", {"work", "desk", "office"}),
                            ("Mobile", {"cell", "mobile"}),
                        )
                        if {t.strip().lower() for t in types} & keywords
                    ),
                    "Other",
                )

                # Ensure all possible nodes exist (create empty ones if missing)
                for _tag in ("Telephone", "Mobile", "Other"):
                    if contact_node.find(_tag) is None:
                        ET.SubElement(contact_node, _tag)

                el = contact_node.find(tag)
                if el is None or el.text:
                    el = ET.SubElement(contact_node, tag)

                # Normalize international prefix and remove non-numeric characters except '*'
                number = re.sub(r"^\+", "00", number)
                number = re.sub(r"[^0-9*]+", "", number)

                el.text = number

        xml_body = ET.tostring(root_node, encoding="utf-8").decode("utf-8")
        xml_str = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            + xml_body
            + "\n"
        )

        if write_path:
            Path(write_path).write_text(xml_str, encoding="utf-8")

        return xml_str


if __name__ == "__main__":
    # Load settings from INI file
    cfg = load_settings(str(Path(__file__).parent / "settings.ini"))

    client = NextcloudWebDAVClient(
        url=cfg["url"],
        username=cfg["username"],
        password=cfg["password"],
        addressbook=cfg["addressbook"],
        # verify_ssl=cfg["verify_ssl"],
    )
    contacts = client.download_all_contacts()

    print(f"Fetched {len(contacts)} contacts from Nextcloud.\n")

    gequdio_xml = client.create_gequdio_contact_xml(
        contacts, write_path=str(Path(__file__).parent / "gequdio.xml")
    )
