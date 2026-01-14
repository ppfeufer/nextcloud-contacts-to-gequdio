# Standard Library
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import ANY, Mock

# Third Party
import pytest
import requests

# Nextcloud Contacts to GEQUDIO
from nextcloud_contacts_to_gequdio import __version__
from nextcloud_contacts_to_gequdio.nextcloud_to_gequdio import (
    NextcloudWebDAVClient,
    load_settings,
)


class TestLoadSettings:
    """
    Test cases for the load_settings function.
    """

    def test_loads_settings_returns_correct_values_for_valid_ini(self):
        """
        Test that load_settings returns correct values for a valid INI file.

        :return:
        :rtype:
        """

        valid_ini = Path("valid.ini")
        valid_ini.write_text(
            "[nextcloud]\nurl=https://example.com\nuser=test_user\npassword=test_pass\naddressbook=my_contacts\nverify_ssl=False"
        )

        result = load_settings(str(valid_ini))

        assert result["url"] == "https://example.com"
        assert result["username"] == "test_user"
        assert result["password"] == "test_pass"
        assert result["addressbook"] == "my_contacts"
        assert result["verify_ssl"] is False

        valid_ini.unlink()

    def test_loads_settings_uses_default_addressbook_when_missing(self):
        """
        Test that load_settings uses default addressbook when missing.

        :return:
        :rtype:
        """

        default_ini = Path("default.ini")
        default_ini.write_text(
            "[nextcloud]\nurl=https://example.com\nuser=test_user\npassword=test_pass\nverify_ssl=True"
        )

        result = load_settings(str(default_ini))

        assert result["addressbook"] == "contacts"

        default_ini.unlink()

    def test_loads_settings_raises_file_not_found_for_nonexistent_file(self):
        """
        Test that load_settings raises FileNotFoundError for nonexistent file.

        :return:
        :rtype:
        """

        with pytest.raises(FileNotFoundError):
            load_settings("nonexistent.ini")

    def test_loads_settings_raises_key_error_for_missing_nextcloud_section(self):
        """
        Test that load_settings raises KeyError for missing nextcloud section.

        :return:
        :rtype:
        """

        invalid_ini = Path("invalid.ini")
        invalid_ini.write_text("[wrong_section]\nkey=value")

        with pytest.raises(KeyError):
            load_settings(str(invalid_ini))

        invalid_ini.unlink()

    def test_loads_settings_sets_default_addressbook_when_empty(self):
        """
        Test that load_settings sets default addressbook when empty.

        :return:
        :rtype:
        """

        empty_ini = Path("empty_addressbook.ini")
        empty_ini.write_text(
            "[nextcloud]\nurl=https://example.com\nuser=test_user\npassword=test_pass\naddressbook=\nverify_ssl=True"
        )

        result = load_settings(str(empty_ini))

        assert result["addressbook"] == "contacts"

        empty_ini.unlink()

    def test_loads_settings_preserves_provided_addressbook(self):
        """
        Test that load_settings preserves provided addressbook.

        :return:
        :rtype:
        """

        custom_ini = Path("custom_addressbook.ini")
        custom_ini.write_text(
            "[nextcloud]\nurl=https://example.com\nuser=test_user\npassword=test_pass\naddressbook=my_contacts\nverify_ssl=True"
        )

        result = load_settings(str(custom_ini))

        assert result["addressbook"] == "my_contacts"

        custom_ini.unlink()


class TestNextcloudWebDAVClientHelperGetUserAgent:
    """
    Test cases for the NextcloudWebDAVClient._get_user_agent method.
    """

    def test_user_agent_contains_correct_app_version(self):
        """
        Test that the user agent contains the correct application version.

        :return:
        :rtype:
        """

        result = NextcloudWebDAVClient._get_user_agent()

        assert f"NextcloudContactsToGEQUDIO/{__version__}" in result

    def test_user_agent_contains_correct_requests_version(self):
        """
        Test that the user agent contains the correct requests library version.

        :return:
        :rtype:
        """

        result = NextcloudWebDAVClient._get_user_agent()

        assert f"python-requests/{requests.__version__}" in result

    def test_user_agent_contains_correct_repository_url(self):
        """
        Test that the user agent contains the correct repository URL.

        :return:
        :rtype:
        """

        result = NextcloudWebDAVClient._get_user_agent()

        assert "+https://github.com/ppfeufer/nextcloud-contacts-to-gequdio" in result


class TestNextcloudWebDAVClientInit:
    def test_nextcloud_client_initializes_with_valid_settings(self):
        """
        Test that NextcloudWebDAVClient initializes with valid settings.

        :return:
        :rtype:
        """

        client = NextcloudWebDAVClient("url", "user", "pass")

        assert client.base_url.endswith("contacts/")


class TestNextcloudWebDAVClientHelperParseVCard:
    """
    Test cases for the NextcloudWebDAVClient._parse_vcard method.
    """

    def test_parse_vcard_handles_vcard_with_no_properties(self):
        """
        Test that _parse_vcard handles a vCard with no properties.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "Unknown"
        assert numbers == []

    def test_parse_vcard_handles_vcard_with_only_whitespace(self):
        """
        Test that _parse_vcard handles a vCard with only whitespace.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\n   \nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "Unknown"
        assert numbers == []

    def test_parse_vcard_handles_vcard_with_invalid_property_format(self):
        """
        Test that _parse_vcard handles a vCard with invalid property format.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nINVALID_PROPERTY\nFN:John Doe\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == []

    def test_parse_vcard_handles_vcard_with_multiple_folded_properties(self):
        """
        Test that _parse_vcard handles a vCard with multiple folded properties.

        :return:
        :rtype:
        """

        vcard = (
            "BEGIN:VCARD\nFN:John\n Doe\nTEL;TYPE=HOME:123\n 456789\n"
            "TEL;TYPE=CELL:987\n 654321\nEND:VCARD"
        )
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == [("123456789", ["home"]), ("987654321", ["cell"])]

    def test_parse_vcard_handles_vcard_with_empty_tel_property(self):
        """
        Test that _parse_vcard handles a vCard with an empty TEL property.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nTEL:\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == []

    def test_parse_vcard_handles_vcard_with_tel_property_without_value(self):
        """
        Test that _parse_vcard handles a vCard with a TEL property without value.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=HOME:\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == []

    def test_parse_vcard_handles_vcard_with_duplicate_properties(self):
        """
        Test that _parse_vcard handles a vCard with duplicate properties.

        :return:
        :rtype:
        """

        vcard = (
            "BEGIN:VCARD\nFN:John Doe\nFN:Jane Doe\n"
            "TEL;TYPE=HOME:123456789\nTEL;TYPE=HOME:987654321\nEND:VCARD"
        )
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "Jane Doe"
        assert numbers == [("123456789", ["home"]), ("987654321", ["home"])]

    def test_parse_vcard_ignores_empty_lines(self):
        """
        Test that _parse_vcard ignores empty lines.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\n\nFN:John Doe\n\nTEL:123456789\n\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == [("123456789", [])]

    def test_parse_vcard_handles_vcard_with_only_empty_lines(self):
        """
        Test that _parse_vcard handles a vCard with only empty lines.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\n\n\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "Unknown"
        assert numbers == []

    def test_parse_vcard_handles_continuation_as_new_property(self):
        """
        Test that _parse_vcard handles continuation as a new property.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\n TEL;TYPE=HOME:123456789\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == [("123456789", ["home"])]

    def test_parse_vcard_handles_continuation_with_invalid_property(self):
        """
        Test that _parse_vcard handles continuation with an invalid property.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\n TELINVALID:123456789\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == []

    def test_parse_vcard_handles_continuation_with_mixed_properties(self):
        """
        Test that _parse_vcard handles continuation with mixed properties.

        :return:
        :rtype:
        """

        vcard = (
            "BEGIN:VCARD\nFN:John\n Doe\n TEL;TYPE=HOME:123\n 456789\n"
            "TEL;TYPE=CELL:987\n 654321\nEND:VCARD"
        )
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == [("123456789", ["home"]), ("987654321", ["cell"])]

    def test_parse_vcard_handles_single_type(self):
        """
        Test that _parse_vcard handles a single type.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=HOME:123456789\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == [("123456789", ["home"])]

    def test_parse_vcard_handles_multiple_types_with_whitespace_and_case(self):
        """
        Test that _parse_vcard handles multiple types with whitespace and case.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE= HOME , Work :123456789\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == [("123456789", ["home", "work"])]

    def test_parse_vcard_handles_flag_style_type_parameter(self):
        """
        Test that _parse_vcard handles flag-style TYPE parameter.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;HOME:123456789\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == [("123456789", ["home"])]

    def test_parse_vcard_ignores_unrelated_parameters_and_extracts_type(self):
        """
        Test that _parse_vcard ignores unrelated parameters and extracts type.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;PREF=1;TYPE=WORK:987654321\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == [("987654321", ["work"])]

    def test_parse_vcard_handles_invalid_type_format_preserving_raw_value(self):
        """
        Test that _parse_vcard handles invalid TYPE format preserving raw value.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=HOME=WORK:123456789\nEND:VCARD"
        name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"
        assert numbers == [("123456789", ["home=work"])]

    def test_parses_prefix_when_n_property_contains_valid_prefix(self):
        """
        Test that _parse_vcard parses prefix when N property contains a valid prefix.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nN:Doe;John;;Dr.;\nEND:VCARD"
        name, _ = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "Dr. John Doe"

    def test_ignores_prefix_when_n_property_is_empty(self):
        """
        Test that _parse_vcard ignores prefix when N property is empty.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:Jane Smith\nN:Smith;Jane;;;\nEND:VCARD"
        name, _ = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "Jane Smith"

    def test_handles_missing_n_property_gracefully(self):
        """
        Test that _parse_vcard handles missing N property gracefully.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:Emily Brown\nEND:VCARD"
        name, _ = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "Emily Brown"

    def test_trims_whitespace_around_prefix_in_n_property(self):
        """
        Test that _parse_vcard trims whitespace around prefix in N property.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nN:Doe;John;;  Dr.  ;\nEND:VCARD"
        name, _ = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "Dr. John Doe"

    def test_ignores_n_property_with_insufficient_components(self):
        """
        Test that _parse_vcard ignores N property with insufficient components.

        :return:
        :rtype:
        """

        vcard = "BEGIN:VCARD\nFN:John Doe\nN:Doe;John;\nEND:VCARD"
        name, _ = NextcloudWebDAVClient._parse_vcard(vcard)

        assert name == "John Doe"


class TestNextcloudWebDAVClientDownloadAllContacts:
    """
    Test cases for the NextcloudWebDAVClient.download_all_contacts method.
    """

    def test_downloads_all_contacts_successfully(self, monkeypatch):
        """
        Test that download_all_contacts successfully retrieves and parses contacts.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = """
        <multistatus xmlns="DAV:">
            <response>
                <href>/contact1.vcf</href>
                <propstat>
                    <prop>
                        <address-data xmlns="urn:ietf:params:xml:ns:carddav">BEGIN:VCARD\nFN:John Doe\nEND:VCARD</address-data>
                    </prop>
                </propstat>
            </response>
            <response>
                <href>/contact2.vcf</href>
                <propstat>
                    <prop>
                        <address-data xmlns="urn:ietf:params:xml:ns:carddav">BEGIN:VCARD\nFN:Jane Doe\nEND:VCARD</address-data>
                    </prop>
                </propstat>
            </response>
        </multistatus>
        """
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )
        client.session = mock_session

        vcards = client.download_all_contacts()

        assert vcards == [
            "BEGIN:VCARD\nFN:John Doe\nEND:VCARD",
            "BEGIN:VCARD\nFN:Jane Doe\nEND:VCARD",
        ]
        mock_session.request.assert_called_once_with(
            method="REPORT",
            url=client.base_url,
            data=ANY,
            headers=ANY,
            verify=client.verify,
        )

    def test_handles_empty_addressbook_response(self, monkeypatch):
        """
        Test that download_all_contacts handles an empty address book response.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = """
        <multistatus xmlns="DAV:"></multistatus>
        """
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )
        client.session = mock_session

        vcards = client.download_all_contacts()

        assert vcards == []
        mock_session.request.assert_called_once_with(
            method="REPORT",
            url=client.base_url,
            data=ANY,
            headers=ANY,
            verify=client.verify,
        )

    def test_handles_non_multistatus_xml_returns_empty_list(self, monkeypatch):
        """
        Test that download_all_contacts handles non-multistatus XML and returns an empty list.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "<invalid>XML</invalid>"
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )
        client.session = mock_session

        vcards = client.download_all_contacts()

        assert vcards == []

    def test_appends_vcard_text_when_address_data_is_present(self, monkeypatch):
        """
        Test that download_all_contacts appends vCard text when address-data is present.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = """
        <multistatus xmlns="DAV:">
            <response>
                <propstat>
                    <prop>
                        <address-data xmlns="urn:ietf:params:xml:ns:carddav">BEGIN:VCARD\nFN:John Doe\nEND:VCARD</address-data>
                    </prop>
                </propstat>
            </response>
        </multistatus>
        """
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )
        client.session = mock_session

        vcards = client.download_all_contacts()

        assert vcards == ["BEGIN:VCARD\nFN:John Doe\nEND:VCARD"]

    def test_skips_vcard_when_address_data_is_missing(self, monkeypatch):
        """
        Test that download_all_contacts skips vCard when address-data is missing.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = """
        <multistatus xmlns="DAV:">
            <response>
                <propstat>
                    <prop>
                        <address-data xmlns="urn:ietf:params:xml:ns:carddav"></address-data>
                    </prop>
                </propstat>
            </response>
        </multistatus>
        """
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )
        client.session = mock_session

        vcards = client.download_all_contacts()

        assert vcards == []

    def test_skips_vcard_when_address_data_tag_is_absent(self, monkeypatch):
        """
        Test that download_all_contacts skips vCard when address-data tag is absent.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = """
        <multistatus xmlns="DAV:">
            <response>
                <propstat>
                    <prop>
                    </prop>
                </propstat>
            </response>
        </multistatus>
        """
        mock_response.raise_for_status = Mock()
        mock_session.request.return_value = mock_response

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )
        client.session = mock_session

        vcards = client.download_all_contacts()

        assert vcards == []


class TestNextcloudWebDAVClientCreateGequdioContactXML:
    """
    Test cases for the NextcloudWebDAVClient.create_gequdio_contact_xml method.
    """

    def test_generates_valid_xml_with_multiple_contacts(self, monkeypatch):
        """
        Test that create_gequdio_contact_xml generates valid XML with multiple contacts.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )

        vcards = [
            "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=work:+123456789\nEND:VCARD",
            "BEGIN:VCARD\nFN:Jane Smith\nTEL;TYPE=mobile:+987654321\nEND:VCARD",
        ]

        xml_output = client.create_gequdio_contact_xml(vcards)

        assert "<Name>John Doe</Name>" in xml_output
        assert "<Telephone>00123456789</Telephone>" in xml_output
        assert "<Name>Jane Smith</Name>" in xml_output
        assert "<Mobile>00987654321</Mobile>" in xml_output

    def test_handles_empty_vcard_list(self, monkeypatch):
        """
        Test that create_gequdio_contact_xml handles an empty vCard list.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )

        xml_output = client.create_gequdio_contact_xml([])
        root = ET.fromstring(xml_output)

        assert root.tag == "GEQUDIODirectory"
        assert len(list(root)) == 0

    def test_normalizes_phone_numbers_correctly(self, monkeypatch):
        """
        Test that create_gequdio_contact_xml normalizes phone numbers correctly.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )

        vcards = [
            "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=work:+1 (234) 567-890\nEND:VCARD",
        ]

        xml_output = client.create_gequdio_contact_xml(vcards)

        assert "<Telephone>001234567890</Telephone>" in xml_output

    def test_assigns_other_tag_for_unknown_phone_types(self, monkeypatch):
        """
        Test that create_gequdio_contact_xml assigns Other tag for unknown phone types.

        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )

        vcards = [
            "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=fax:+123456789\nEND:VCARD",
        ]

        xml_output = client.create_gequdio_contact_xml(vcards)

        assert "<Other>00123456789</Other>" in xml_output

    def test_writes_output_to_file_when_path_is_provided(self, tmp_path, monkeypatch):
        """
        Test that create_gequdio_contact_xml writes output to file when path is provided.

        :param tmp_path:
        :type tmp_path:
        :param monkeypatch:
        :type monkeypatch:
        :return:
        :rtype:
        """

        client = NextcloudWebDAVClient(
            url="https://example.com",
            username="user",
            password="pass",
            addressbook="contacts",
        )

        vcards = [
            "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=work:+123456789\nEND:VCARD",
        ]

        output_path = tmp_path / "output.xml"
        client.create_gequdio_contact_xml(vcards, write_path=str(output_path))

        assert output_path.read_text(encoding="utf-8").startswith('<?xml version="1.0"')


class TestNextcloudWebDAVClientHelperExtractTelTypes:
    """
    Test cases for the NextcloudWebDAVClient._extract_tel_types method.
    """

    def test_extracts_single_type_correctly(self):
        """
        Test that _extract_tel_types extracts a single type correctly.

        :return:
        :rtype:
        """

        key = "TEL;TYPE=work:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == ["work"]

    def test_extracts_multiple_types_correctly(self):
        """
        Test that _extract_tel_types extracts multiple types correctly.

        :return:
        :rtype:
        """

        key = "TEL;TYPE=work,cell:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == ["work", "cell"]

    def test_handles_key_without_type_parameter(self):
        """
        Test that _extract_tel_types handles a key without a TYPE parameter.

        :return:
        :rtype:
        """

        key = "TEL:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == []

    def test_ignores_empty_type_values(self):
        """
        Test that _extract_tel_types ignores empty type values.

        :return:
        :rtype:
        """

        key = "TEL;TYPE=,:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == []

    def test_extracts_types_with_extra_parameters(self):
        """
        Test that _extract_tel_types extracts types with extra parameters.

        :return:
        :rtype:
        """

        key = "TEL;TYPE=work;PREF=1:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == ["work"]

    def test_handles_whitespace_in_type_values(self):
        """
        Test that _extract_tel_types handles whitespace in type values.

        :return:
        :rtype:
        """

        key = "TEL;TYPE= work , cell :123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == ["work", "cell"]

    def test_handles_flag_style_parameters(self):
        """
        Test that _extract_tel_types handles flag-style parameters.

        :return:
        :rtype:
        """

        key = "TEL;HOME:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == ["home"]

    def test_preserves_malformed_type_values(self):
        """
        Test that _extract_tel_types preserves malformed type values.

        :return:
        :rtype:
        """

        key = "TEL;TYPE=home=work:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == ["home=work"]

    def test_returns_empty_list_for_invalid_key(self):
        """
        Test that _extract_tel_types returns an empty list for an invalid key.

        :return:
        :rtype:
        """

        key = "INVALID_KEY"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == []

    def test_handles_key_with_no_parameters(self):
        """
        Test that _extract_tel_types handles a key with no parameters.

        :return:
        :rtype:
        """

        key = "TEL:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == []

    def rtest_eturns_empty_list_when_key_is_none(self):
        """
        Test that _extract_tel_types returns an empty list when key is None.

        :return:
        :rtype:
        """

        key = None

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == []

    def test_returns_empty_list_when_key_is_empty_string(self):
        """
        Test that _extract_tel_types returns an empty list when key is an empty string.

        :return:
        :rtype:
        """

        key = ""

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == []

    def test_skips_processing_when_parameter_is_empty(self):
        """
        Test that _extract_tel_types skips processing when a parameter is empty.

        :return:
        :rtype:
        """

        key = "TEL;TYPE=work;:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == ["work"]

    def test_skips_processing_when_parameter_is_whitespace(self):
        """
        Test that _extract_tel_types skips processing when a parameter is whitespace.

        :return:
        :rtype:
        """

        key = "TEL;TYPE=work; ;:123456789"

        types = NextcloudWebDAVClient._extract_tel_types(key)

        assert types == ["work"]


class TestNextcloudWebDAVClientHelperUnfoldLines:
    """
    Test cases for the NextcloudWebDAVClient._unfold_lines method.
    """

    def test_unfolds_lines_with_continuation(self):
        """
        Test that _unfold_lines unfolds lines with continuation.

        :return:
        :rtype:
        """

        lines = ["TEL;TYPE=work:123456789", " 456"]
        pattern = re.compile(r"^[A-Za-z0-9\-]+(?:;.*)?:")

        unfolded = NextcloudWebDAVClient._unfold_lines(lines, pattern)

        assert unfolded == ["TEL;TYPE=work:123456789456"]

    def test_unfolds_lines_with_multiple_continuations(self):
        """
        Test that _unfold_lines unfolds lines with multiple continuations.

        :return:
        :rtype:
        """

        lines = ["TEL;TYPE=work:123", " 456", " 789"]
        pattern = re.compile(r"^[A-Za-z0-9\-]+(?:;.*)?:")

        unfolded = NextcloudWebDAVClient._unfold_lines(lines, pattern)

        assert unfolded == ["TEL;TYPE=work:123456789"]

    def test_skips_empty_lines(self):
        """
        Test that _unfold_lines skips empty lines.

        :return:
        :rtype:
        """

        lines = ["TEL;TYPE=work:123456789", "", " 456"]
        pattern = re.compile(r"^[A-Za-z0-9\-]+(?:;.*)?:")

        unfolded = NextcloudWebDAVClient._unfold_lines(lines, pattern)

        assert unfolded == ["TEL;TYPE=work:123456789456"]

    def test_handles_lines_without_continuation(self):
        """
        Test that _unfold_lines handles lines without continuation.

        :return:
        :rtype:
        """

        lines = ["TEL;TYPE=work:123456789"]
        pattern = re.compile(r"^[A-Za-z0-9\-]+(?:;.*)?:")

        unfolded = NextcloudWebDAVClient._unfold_lines(lines, pattern)

        assert unfolded == ["TEL;TYPE=work:123456789"]

    def test_unfolds_lines_with_non_tel_properties(self):
        """
        Test that _unfold_lines unfolds lines with non-TEL properties.

        :return:
        :rtype:
        """

        lines = ["FN:John Doe", " TEL;TYPE=work:123456789"]
        pattern = re.compile(r"^[A-Za-z0-9\-]+(?:;.*)?:")

        unfolded = NextcloudWebDAVClient._unfold_lines(lines, pattern)

        assert unfolded == ["FN:John Doe", "TEL;TYPE=work:123456789"]

    def test_preserves_whitespace_in_non_tel_properties(self):
        """
        Test that _unfold_lines preserves whitespace in non-TEL properties.

        :return:
        :rtype:
        """

        lines = ["FN:John", " Doe"]
        pattern = re.compile(r"^[A-Za-z0-9\-]+(?:;.*)?:")

        unfolded = NextcloudWebDAVClient._unfold_lines(lines, pattern)

        assert unfolded == ["FN:John Doe"]

    def test_handles_lines_with_tabs_as_continuation(self):
        """
        Test that _unfold_lines handles lines with tabs as continuation.

        :return:
        :rtype:
        """

        lines = ["TEL;TYPE=work:123", "\t456"]
        pattern = re.compile(r"^[A-Za-z0-9\-]+(?:;.*)?:")

        unfolded = NextcloudWebDAVClient._unfold_lines(lines, pattern)

        assert unfolded == ["TEL;TYPE=work:123456"]
