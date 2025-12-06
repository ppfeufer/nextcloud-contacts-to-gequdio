"""
Nextcloud Contacts to GEQUDIO Contact XML Converter

This script connects to a Nextcloud instance via WebDAV, retrieves contacts from a specified addressbook,
and converts them into GEQUDIO-compatible contact XML format.

Requirements:
- requests

"""

# Standard Library
import configparser
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

# Third Party
import requests
from requests.auth import HTTPBasicAuth

APP_VERSION = "1.0.0"


def _get_user_agent() -> str:
    """
    Returns a default User-Agent string for HTTP requests.

    :return: User-Agent string
    :rtype: str
    """

    return f"NextcloudContactsToGEQUDIO/{APP_VERSION} (+https://github.com/ppfeufer/nextcloud-contacts-to-gequdio) via python-requests/{requests.__version__}"


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

    def _parse_vcard(self, vcard: str) -> tuple[str, list[tuple[str, list[str]]]]:
        """
        Parses a vCard string to extract the full name and telephone numbers with types.

        :param vcard: vCard string
        :type vcard: str
        :return: Tuple of full name and list of (number, [types])
        :rtype: Tuple[str, List[Tuple[str, List[str]]]]
        """

        def unfold_lines(vcard: str) -> list[str]:
            """
            Unfolds folded lines in a vCard string.

            :param vcard: vCard string
            :type vcard: str
            :return: List of unfolded lines
            :rtype: List[str]
            """

            lines = vcard.splitlines()
            out = []

            for line in lines:
                if not line:
                    continue

                if line.startswith((" ", "\t")) and out:
                    out[-1] += line.lstrip()
                else:
                    out.append(line)

            return out

        fn, tels = None, []

        for line in unfold_lines(vcard):
            if line.upper().startswith("FN:"):
                fn = line.split(":", 1)[1].strip()
            elif line.upper().startswith("TEL"):
                parts = line.split(":", 1)
                number = parts[1].strip().split(":", 1)[-1]
                types = [
                    t.strip().lower()
                    for t in parts[0].split(";")[1:]
                    if "=" in t
                    for t in t.split("=", 1)[1].split(",")
                ]
                tels.append((number, types))

        return fn or "Unknown", tels

    def _propfind(self, depth: str = "1"):
        """
        Internal method to perform a PROPFIND request.

        :param depth: Depth header value ("0", "1", or "infinity")
        :type depth: str
        :return: Response XML text
        :rtype: str
        """

        body = """<?xml version="1.0"?>
<d:propfind xmlns:d="DAV:">
    <d:prop>
        <d:getetag/>
        <d:getcontenttype/>
        <d:displayname/>
    </d:prop>
</d:propfind>"""
        # ensure a User-Agent is present on the session
        self.session.headers.update({"User-Agent": _get_user_agent()})

        headers = {
            "Content-Type": 'application/xml; charset="utf-8"',
            "Depth": depth,
        }

        resp = self.session.request(
            method="PROPFIND",
            url=self.base_url,
            data=body.encode("utf-8"),
            headers=headers,
            verify=self.verify,
        )

        resp.raise_for_status()

        return resp.text

    def _unfold_vcard_lines(self, vcard: str) -> list[str]:
        """
        Unfolds folded lines in a vCard string.

        :param vcard: vCard string
        :type vcard: str
        :return: List of unfolded lines
        :rtype: List[str]
        """

        lines = vcard.splitlines()
        out = []

        for line in lines:
            if not line:
                continue

            if line[0] in (" ", "\t") and out:
                out[-1] += line.lstrip()
            else:
                out.append(line)

        return out

    def list_contacts(self) -> list[dict]:
        """
        Lists contact entries in the addressbook.

        :return: List of dicts with contact info
        :rtype:  List[dict]
        """

        root = ET.fromstring(self._propfind())
        results = []

        for response in root.findall(".//{DAV:}response"):
            href = response.find("{DAV:}href")
            prop = response.find(".//{DAV:}prop")

            if href is not None and prop is not None:
                results.append(
                    {
                        "href": href.text,
                        "content_type": prop.findtext("{DAV:}getcontenttype", ""),
                        "etag": prop.findtext("{DAV:}getetag", ""),
                        "displayname": prop.findtext("{DAV:}displayname", ""),
                    }
                )

        return results

    def get_contact(self, href: str) -> str:
        """
        Retrieves the vCard content of a contact entry.

        :param href: Href of the contact entry
        :type href: str
        :return: vCard string
        :rtype: str
        """

        resp = self.session.get(
            url=urljoin(base=self.base_url, url=href), verify=self.verify
        )
        resp.raise_for_status()

        return resp.text

    def download_all_contacts(self) -> list[str]:
        """
        Downloads all contacts as vCard strings.

        :return: List of vCard strings
        :rtype: List[str]
        """

        return [
            self.get_contact(item["href"])
            for item in self.list_contacts()
            if "vcard" in (item.get("content_type", "").lower())
        ]

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

        # sort contacts by full name (case-insensitive) before processing
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
                            ("Telephone", {"work", "desk", "office", "home"}),
                            ("Mobile", {"cell", "mobile"}),
                        )
                        if {t.strip().lower() for t in types} & keywords
                    ),
                    "Other",
                )

                # ensure all possible nodes exist (create empty ones if missing)
                for _tag in ("Telephone", "Mobile", "Other"):
                    if contact_node.find(_tag) is None:
                        ET.SubElement(contact_node, _tag)

                el = contact_node.find(tag)
                if el is None or el.text:
                    el = ET.SubElement(contact_node, tag)
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
