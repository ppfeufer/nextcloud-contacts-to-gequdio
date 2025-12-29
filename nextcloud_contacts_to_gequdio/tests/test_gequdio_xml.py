# Standard Library
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


def test_loads_settings_returns_correct_values_for_valid_ini():
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


def test_loads_settings_uses_default_addressbook_when_missing():
    default_ini = Path("default.ini")
    default_ini.write_text(
        "[nextcloud]\nurl=https://example.com\nuser=test_user\npassword=test_pass\nverify_ssl=True"
    )
    result = load_settings(str(default_ini))
    assert result["addressbook"] == "contacts"
    default_ini.unlink()


def test_loads_settings_raises_file_not_found_for_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        load_settings("nonexistent.ini")


def test_loads_settings_raises_key_error_for_missing_nextcloud_section():
    invalid_ini = Path("invalid.ini")
    invalid_ini.write_text("[wrong_section]\nkey=value")
    with pytest.raises(KeyError):
        load_settings(str(invalid_ini))
    invalid_ini.unlink()


def test_loads_settings_sets_default_addressbook_when_empty():
    empty_ini = Path("empty_addressbook.ini")
    empty_ini.write_text(
        "[nextcloud]\nurl=https://example.com\nuser=test_user\npassword=test_pass\naddressbook=\nverify_ssl=True"
    )
    result = load_settings(str(empty_ini))
    assert result["addressbook"] == "contacts"
    empty_ini.unlink()


def test_loads_settings_preserves_provided_addressbook():
    custom_ini = Path("custom_addressbook.ini")
    custom_ini.write_text(
        "[nextcloud]\nurl=https://example.com\nuser=test_user\npassword=test_pass\naddressbook=my_contacts\nverify_ssl=True"
    )
    result = load_settings(str(custom_ini))
    assert result["addressbook"] == "my_contacts"
    custom_ini.unlink()


def test_user_agent_contains_correct_app_version():
    result = NextcloudWebDAVClient._get_user_agent()
    assert f"NextcloudContactsToGEQUDIO/{__version__}" in result


def test_user_agent_contains_correct_requests_version():
    result = NextcloudWebDAVClient._get_user_agent()
    assert f"python-requests/{requests.__version__}" in result


def test_user_agent_contains_correct_repository_url():
    result = NextcloudWebDAVClient._get_user_agent()
    assert "+https://github.com/ppfeufer/nextcloud-contacts-to-gequdio" in result


# NextcloudWebDAVClient.__init__
def test_nextcloud_client_initializes_with_valid_settings():
    client = NextcloudWebDAVClient("url", "user", "pass")
    assert client.base_url.endswith("contacts/")


# NextcloudWebDAVClient.get_contact()
def test_nextcloud_client_raises_for_invalid_contact_href():
    client = NextcloudWebDAVClient("url", "user", "pass")
    with pytest.raises(Exception):
        client.get_contact("invalid_href")


# NextcloudWebDAVClient._parse_vcard()
def test_parse_vcard_handles_vcard_with_no_properties():
    vcard = "BEGIN:VCARD\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "Unknown"
    assert numbers == []


def test_parse_vcard_handles_vcard_with_only_whitespace():
    vcard = "BEGIN:VCARD\n   \nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "Unknown"
    assert numbers == []


def test_parse_vcard_handles_vcard_with_invalid_property_format():
    vcard = "BEGIN:VCARD\nINVALID_PROPERTY\nFN:John Doe\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == []


def test_parse_vcard_handles_vcard_with_multiple_folded_properties():
    vcard = (
        "BEGIN:VCARD\nFN:John\n Doe\nTEL;TYPE=HOME:123\n 456789\n"
        "TEL;TYPE=CELL:987\n 654321\nEND:VCARD"
    )
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == [("123456789", ["home"]), ("987654321", ["cell"])]


def test_parse_vcard_handles_vcard_with_empty_tel_property():
    vcard = "BEGIN:VCARD\nFN:John Doe\nTEL:\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == []


def test_parse_vcard_handles_vcard_with_tel_property_without_value():
    vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=HOME:\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == []


def test_parse_vcard_handles_vcard_with_duplicate_properties():
    vcard = (
        "BEGIN:VCARD\nFN:John Doe\nFN:Jane Doe\n"
        "TEL;TYPE=HOME:123456789\nTEL;TYPE=HOME:987654321\nEND:VCARD"
    )
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "Jane Doe"
    assert numbers == [("123456789", ["home"]), ("987654321", ["home"])]


def test_parse_vcard_ignores_empty_lines():
    vcard = "BEGIN:VCARD\n\nFN:John Doe\n\nTEL:123456789\n\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == [("123456789", [])]


def test_parse_vcard_handles_vcard_with_only_empty_lines():
    vcard = "BEGIN:VCARD\n\n\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "Unknown"
    assert numbers == []


def test_parse_vcard_handles_continuation_as_new_property():
    vcard = "BEGIN:VCARD\nFN:John Doe\n TEL;TYPE=HOME:123456789\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == [("123456789", ["home"])]


def test_parse_vcard_handles_continuation_with_invalid_property():
    vcard = "BEGIN:VCARD\nFN:John Doe\n TELINVALID:123456789\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == []


def test_parse_vcard_handles_continuation_with_mixed_properties():
    vcard = (
        "BEGIN:VCARD\nFN:John\n Doe\n TEL;TYPE=HOME:123\n 456789\n"
        "TEL;TYPE=CELL:987\n 654321\nEND:VCARD"
    )
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == [("123456789", ["home"]), ("987654321", ["cell"])]


def test_parse_vcard_handles_single_type():
    vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=HOME:123456789\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == [("123456789", ["home"])]


def test_parse_vcard_handles_multiple_types_with_whitespace_and_case():
    vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE= HOME , Work :123456789\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == [("123456789", ["home", "work"])]


def test_parse_vcard_handles_flag_style_type_parameter():
    vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;HOME:123456789\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == [("123456789", ["home"])]


def test_parse_vcard_ignores_unrelated_parameters_and_extracts_type():
    vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;PREF=1;TYPE=WORK:987654321\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == [("987654321", ["work"])]


def test_parse_vcard_handles_invalid_type_format_preserving_raw_value():
    vcard = "BEGIN:VCARD\nFN:John Doe\nTEL;TYPE=HOME=WORK:123456789\nEND:VCARD"
    name, numbers = NextcloudWebDAVClient._parse_vcard(vcard)
    assert name == "John Doe"
    assert numbers == [("123456789", ["home=work"])]


# NextcloudWebDAVClient._propfind()
def test_propfind_returns_valid_response_for_depth_1(monkeypatch):
    mock_session = Mock()
    mock_response = Mock()
    mock_response.text = "<response>Valid XML</response>"
    mock_response.raise_for_status = Mock()
    mock_session.request.return_value = mock_response

    client = NextcloudWebDAVClient(
        url="https://example.com",
        username="user",
        password="pass",
        addressbook="contacts",
    )
    client.session = mock_session

    response = client._propfind(depth="1")
    assert response == "<response>Valid XML</response>"
    mock_session.request.assert_called_once_with(
        method="PROPFIND",
        url=client.base_url,
        data=ANY,
        headers=ANY,
        verify=client.verify,
    )


def test_propfind_raises_exception_for_invalid_response(monkeypatch):
    mock_session = Mock()
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    mock_session.request.return_value = mock_response

    client = NextcloudWebDAVClient(
        url="https://example.com",
        username="user",
        password="pass",
        addressbook="contacts",
    )
    client.session = mock_session

    with pytest.raises(Exception, match="HTTP Error"):
        client._propfind(depth="1")


def test_propfind_sends_correct_headers(monkeypatch):
    mock_session = Mock()
    mock_response = Mock()
    mock_response.text = "<response>Valid XML</response>"
    mock_response.raise_for_status = Mock()
    mock_session.request.return_value = mock_response

    client = NextcloudWebDAVClient(
        url="https://example.com",
        username="user",
        password="pass",
        addressbook="contacts",
    )
    client.session = mock_session

    client._propfind(depth="1")
    headers = {
        "Content-Type": 'application/xml; charset="utf-8"',
        "Depth": "1",
    }
    mock_session.request.assert_called_once_with(
        method="PROPFIND",
        url=client.base_url,
        data=ANY,
        headers=headers,
        verify=client.verify,
    )


def test_propfind_handles_different_depth_values(monkeypatch):
    mock_session = Mock()
    mock_response = Mock()
    mock_response.text = "<response>Valid XML</response>"
    mock_response.raise_for_status = Mock()
    mock_session.request.return_value = mock_response

    client = NextcloudWebDAVClient(
        url="https://example.com",
        username="user",
        password="pass",
        addressbook="contacts",
    )
    client.session = mock_session

    for depth in ["0", "1", "infinity"]:
        response = client._propfind(depth=depth)
        assert response == "<response>Valid XML</response>"
        mock_session.request.assert_called_with(
            method="PROPFIND",
            url=client.base_url,
            data=ANY,
            headers={
                "Content-Type": 'application/xml; charset="utf-8"',
                "Depth": depth,
            },
            verify=client.verify,
        )


# NextcloudWebDAVClient.get_contact()
def test_retrieves_vcard_content_successfully(monkeypatch):
    mock_session = Mock()
    mock_response = Mock()
    mock_response.text = "BEGIN:VCARD\nFN:John Doe\nEND:VCARD"
    mock_response.raise_for_status = Mock()
    mock_session.get.return_value = mock_response

    client = NextcloudWebDAVClient(
        url="https://example.com",
        username="user",
        password="pass",
        addressbook="contacts",
    )
    client.session = mock_session

    vcard = client.get_contact(href="contact.vcf")
    assert vcard == "BEGIN:VCARD\nFN:John Doe\nEND:VCARD"
    mock_session.get.assert_called_once_with(
        url="https://example.com/remote.php/dav/addressbooks/users/user/contacts/contact.vcf",
        verify=client.verify,
    )


def test_raises_exception_for_invalid_response(monkeypatch):
    mock_session = Mock()
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    mock_session.get.return_value = mock_response

    client = NextcloudWebDAVClient(
        url="https://example.com",
        username="user",
        password="pass",
        addressbook="contacts",
    )
    client.session = mock_session

    with pytest.raises(Exception, match="HTTP Error"):
        client.get_contact(href="contact.vcf")


# NextcloudWebDAVClient.download_all_contacts()
def test_downloads_all_contacts_successfully(monkeypatch):
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


def test_handles_empty_addressbook_response(monkeypatch):
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


def test_handles_non_multistatus_xml_returns_empty_list(monkeypatch):
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


def test_appends_vcard_text_when_address_data_is_present(monkeypatch):
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


def test_skips_vcard_when_address_data_is_missing(monkeypatch):
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


def test_skips_vcard_when_address_data_tag_is_absent(monkeypatch):
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


# NextcloudWebDAVClient.create_gequdio_contact_xml()
def test_generates_valid_xml_with_multiple_contacts(monkeypatch):
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


def test_handles_empty_vcard_list(monkeypatch):
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


def test_normalizes_phone_numbers_correctly(monkeypatch):
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


def test_assigns_other_tag_for_unknown_phone_types(monkeypatch):
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


def test_writes_output_to_file_when_path_is_provided(tmp_path, monkeypatch):
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
