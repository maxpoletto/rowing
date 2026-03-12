"""
Shared EFA XML parsing utilities.

Common parsing logic for boats, persons, destinations, seats, and distances
used by both efa_importer.py and efa_viewer.py.
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Optional

logger = logging.getLogger(__name__)


def parse_distance(distance_str: str) -> Optional[int]:
    """Parse distance string like '8 km', '10.5 km' and return rounded km as integer."""
    if not distance_str:
        return 0
    match = re.search(r'(\d+(?:\.\d+)?)', distance_str)
    return round(float(match.group(1))) if match else 0


def parse_seats(seats_str: str) -> int:
    """Parse seats string like '4X', '8', '2' and return integer."""
    if not seats_str or seats_str == "unknown":
        return 0
    match = re.search(r'(\d+)', seats_str)
    return int(match.group(1)) if match else 0


def parse_boats(xml_file: str) -> dict:
    """Parse boats.efa2boats and return {variant_id: boat_data} dict.

    Each boat variant gets an ID of the form '{uuid}-v{n}'.
    Boat data keys: id, oid, name, size, rig, cox, and optionally suffix.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    boats = {}

    for record in root.findall(".//record"):
        boat_id = record.find("Id").text
        name = record.find("Name").text
        name_affix = record.find("NameAffix")

        type_seats = record.find("TypeSeats").text.split(";")
        type_rigging = record.find("TypeRigging").text.split(";")
        type_coxing = record.find("TypeCoxing").text.split(";")

        if len(type_seats) != len(type_rigging) or len(type_seats) != len(type_coxing):
            logger.warning(f"Boat {name} ({boat_id}) has inconsistent variant counts: skipping")
            continue

        n_variants = len(type_seats)
        last_variant = int(record.find("LastVariant").text)
        if n_variants != last_variant:
            logger.warning(f"Boat {name} ({boat_id}) has {n_variants} variants but LastVariant={last_variant}: using {n_variants}")

        for variant in range(1, n_variants + 1):
            variant_id = f"{boat_id}-v{variant}"
            boat_data = {
                "id": variant_id,
                "oid": boat_id,
                "name": name,
                "size": parse_seats(type_seats[variant - 1]),
                "rig": type_rigging[variant - 1].lower(),
                "cox": type_coxing[variant - 1].lower(),
            }
            if name_affix is not None:
                boat_data["suffix"] = name_affix.text
            boats[variant_id] = boat_data

    return boats


def parse_persons(xml_file: str) -> dict:
    """Parse persons.efa2persons and return {person_id: person_data} dict.

    Person data keys: id, sex, and optionally fn, ln, del, hid.
    fn/ln are omitted when None (not all records have both names).
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    persons = {}

    for record in root.findall(".//record"):
        person_id = record.find("Id").text
        first_name_elem = record.find("FirstName")
        last_name_elem = record.find("LastName")
        gender = record.find("Gender").text

        last_name = last_name_elem.text if last_name_elem is not None else None
        first_name = first_name_elem.text if first_name_elem is not None else None

        if last_name and last_name.startswith("archiveID:"):
            continue

        person_data = {
            "id": person_id,
            "sex": 'm' if gender.lower() == 'male' else 'f' if gender.lower() == 'female' else 'u',
            # Unclear what these mean in EFA since persons with these flags
            # still appear in logbooks.
            "del": record.find("Deleted") is not None,
            "hid": record.find("Invisible") is not None,
        }
        if first_name:
            person_data["fn"] = first_name
        if last_name:
            person_data["ln"] = last_name

        persons[person_id] = person_data

    return persons


def parse_destinations(xml_file: str) -> dict:
    """Parse destinations.efa2destinations and return {dest_id: dest_data} dict.

    Destination data keys: id, name, and optionally dist.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    destinations = {}

    for record in root.findall(".//record"):
        dest_id = record.find("Id").text
        name = record.find("Name").text
        dest_data = {
            "id": dest_id,
            "name": name,
        }
        distance_elem = record.find("Distance")
        if distance_elem is not None:
            dest_data["dist"] = parse_distance(distance_elem.text)
        destinations[dest_id] = dest_data

    return destinations


def format_person_name(first_name: Optional[str], last_name: Optional[str]) -> str:
    """Format person name for display."""
    if first_name and last_name:
        return f"{first_name} {last_name}"
    return last_name or first_name or "Unknown"
