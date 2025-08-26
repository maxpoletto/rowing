#!/usr/bin/env python3
"""
EFA Backup Importer

Converts EFA rowing club backup files (XML format) to normalized JSON files
for web viewing.
"""

import argparse
import glob
import gzip
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class EFAImporter:
    def __init__(self):
        self.stats = {
            "excessive_distances": 0,
            "future_years": 0,
            "missing_boats": 0,
        }
        self.boats = {}
        self.persons = {}
        self.destinations = {}
        self.logbooks = []
        self.former_counter = 0
        # Track former entities by name to avoid duplicates
        self.former_boats_by_name = {}  # name -> id
        self.former_persons_by_name = {}  # name -> id
        self.former_destinations_by_name = {}  # name -> id

    def generate_former_id(self) -> str:
        """Generate pseudo-ID for former entities"""
        self.former_counter += 1
        return f"former-{self.former_counter:06d}"

    def parse_distance(self, distance_str: str) -> Optional[int]:
        """Parse distance string and return rounded km as integer"""
        if not distance_str:
            return 0

        # Extract number from strings like "8 km", "10.5 km"
        match = re.search(r'(\d+(?:\.\d+)?)', distance_str)
        if match:
            return round(float(match.group(1)))
        return 0

    def parse_seats(self, seats_str: str) -> int:
        """Parse seats string like '4X', '8', '2' and return integer"""
        if not seats_str or seats_str == "unknown":
            return 0

        # Extract number from strings like "4X", "8", "2"
        match = re.search(r'(\d+)', seats_str)
        if match:
            return int(match.group(1))
        return 0

    def parse_date(self, date_str: str) -> Dict[str, Any]:
        """Parse DD.MM.YYYY date and extract year"""
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            return {
                "date": date_str,
                "year": dt.year
            }
        except ValueError:
            return {"date": date_str, "year": None}

    def process_boats(self, xml_file: str):
        """Process boats.efa2boats file"""
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for record in root.findall(".//record"):
            boat_id = record.find("Id").text
            name = record.find("Name").text
            name_affix = record.find("NameAffix")

            # Handle boat variants and possible errors
            last_variant = int(record.find("LastVariant").text)
            type_seats = record.find("TypeSeats").text.split(";")
            type_rigging = record.find("TypeRigging").text.split(";")
            type_coxing = record.find("TypeCoxing").text.split(";")

            if len(type_seats) != len(type_rigging) or len(type_seats) != len(type_coxing):
                logger.warning(f"Boat {name} ({boat_id}) has inconsistent variant counts: skipping")
                logger.debug(f"Full XML record: {ET.tostring(record, encoding='utf-8').decode('utf-8')}")
                continue

            n_variants = len(type_seats)
            if n_variants != last_variant:
                logger.warning(f"Boat {name} ({boat_id}) has {n_variants} variants but LastVariant={last_variant}: using {n_variants}")

            for variant in range(1, n_variants + 1):
                variant_id = f"{boat_id}-v{variant}"

                boat_data = {
                    "id": variant_id,
                    "oid": boat_id,
                    "name": name,
                    "size": self.parse_seats(type_seats[variant - 1]),
                    "rig": type_rigging[variant - 1].lower(),
                    "cox": type_coxing[variant - 1].lower(),
                    "fmr": False
                }

                if name_affix is not None:
                    boat_data["suffix"] = name_affix.text

                self.boats[variant_id] = boat_data

    def process_persons(self, xml_file: str):
        """Process persons.efa2persons file"""
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for record in root.findall(".//record"):
            person_id = record.find("Id").text
            first_name_elem = record.find("FirstName")
            last_name_elem = record.find("LastName")
            gender = record.find("Gender").text

            # Not all records have FirstName and LastName
            last_name = last_name_elem.text if last_name_elem is not None else None
            first_name = first_name_elem.text if first_name_elem is not None else None

            # Skip archived persons (placeholders for deleted members)
            if last_name and last_name.startswith("archiveID:"):
                continue

            person_data = {
                "id": person_id,
                "sex": gender.lower(),
                # We record these but unclear what these mean in EFA, since persons
                # with these flags still appear in logbooks.
                "del": record.find("Deleted") is not None,
                "hid": record.find("Invisible") is not None,
            }
            if first_name:
                person_data["fn"] = first_name
            if last_name:
                person_data["ln"] = last_name

            self.persons[person_id] = person_data

    def process_destinations(self, xml_file: str):
        """Process destinations.efa2destinations file"""
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for record in root.findall(".//record"):
            dest_id = record.find("Id").text
            name = record.find("Name").text

            dest_data = {
                "id": dest_id,
                "name": name,
            }
            if record.find("Distance") is not None:
                dest_data["dist"] = self.parse_distance(record.find("Distance").text)

            self.destinations[dest_id] = dest_data

    def resolve_or_create_entity(self, entity_id: str, entity_type: str, name: str = None) -> str:
        """Resolve entity ID or create former entity if referenced by name"""
        entity_dict = getattr(self, f"{entity_type}s")

        # Check if it's a UUID (existing entity)
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', entity_id):
            # For boats, need to find the variant ID
            if entity_type == "boat":
                # Find matching boat variant (default to variant 1)
                variant_id = f"{entity_id}-v1"
                if variant_id in entity_dict:
                    return variant_id
                # Find any variant of this boat
                for boat_id in entity_dict:
                    if boat_id.startswith(f"{entity_id}-v"):
                        return boat_id
                # Boat UUID exists in XML but we don't have it in our boats dict
                # This shouldn't happen if we processed boats first
            else:
                # For persons and destinations, direct lookup
                if entity_id in entity_dict:
                    return entity_id

        # Check if we've already created a former entity with this name
        former_lookup = getattr(self, f"former_{entity_type}s_by_name")
        if entity_id in former_lookup:
            return former_lookup[entity_id]

        # Create new former entity
        former_id = self.generate_former_id()
        former_lookup[entity_id] = former_id

        if entity_type == "person":
            # Parse "First Last" format for persons referenced by name in logbooks
            name_parts = entity_id.strip().split(None, 1)  # Split on first whitespace
            if len(name_parts) == 2:
                first_name, last_name = name_parts
            elif len(name_parts) == 1:
                first_name = None
                last_name = name_parts[0]
            else:
                first_name = None
                last_name = entity_id

            entity_dict[former_id] = {
                "id": former_id,
                "fn": first_name,
                "ln": last_name,
                "sex": "unknown",
                "fmr": True
            }
        elif entity_type == "boat":
            entity_dict[former_id] = {
                "id": former_id,
                "oid": former_id,
                "name": entity_id,
                "size": 0,
                "rig": "unknown",
                "cox": "unknown",
                "fmr": True
            }
        elif entity_type == "destination":
            entity_dict[former_id] = {
                "id": former_id,
                "name": entity_id,
                "fmr": True
            }

        return former_id

    def process_logbooks(self, xml_files: List[str]):
        """Process logbook files"""
        current_year = datetime.now().year

        for xml_file in xml_files:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for record in root.findall(".//record"):
                entry = {}

                date_info = self.parse_date(record.find("Date").text)
                entry["year"] = date_info["year"]
                entry["date"] = date_info["date"]

                # Filter out future years
                if entry["year"] and entry["year"] > current_year:
                    logger.warning(f"Skipping entry with future year {entry['year']} (date: {entry['date']})")
                    logger.debug(f"Full XML record: {ET.tostring(record, encoding='utf-8').decode('utf-8')}")
                    self.stats["future_years"] += 1
                    continue

                start_time = record.find("StartTime")
                if start_time is not None:
                    entry["t0"] = start_time.text[:-3] # Remove ':00' seconds

                end_time = record.find("EndTime")
                if end_time is not None:
                    entry["t1"] = end_time.text[:-3] # Remove ':00' seconds

                # Boat - can be referenced by ID or name
                boat_id_elem = record.find("BoatId")
                boat_name_elem = record.find("BoatName")

                if boat_id_elem is not None and boat_id_elem.text:
                    boat_variant_elem = record.find("BoatVariant")
                    boat_variant = int(boat_variant_elem.text) if boat_variant_elem is not None else 1
                    # Construct the full variant ID and check if it exists
                    full_boat_id = f"{boat_id_elem.text}-v{boat_variant}"
                    if full_boat_id in self.boats:
                        entry["boat"] = full_boat_id
                    else:
                        logger.warning(f"Boat {full_boat_id} not found in boats.efa2boats")
                        logger.debug(f"Full XML record: {ET.tostring(record, encoding='utf-8').decode('utf-8')}")
                        self.stats["missing_boats"] += 1
                        if boat_name_elem is not None:
                            entry["boat"] = self.resolve_or_create_entity(boat_name_elem.text, "boat")
                elif boat_name_elem is not None and boat_name_elem.text:
                    entry["boat"] = self.resolve_or_create_entity(boat_name_elem.text, "boat")

                # Crew - can be referenced by ID or name
                crew = []
                for i in range(1, 20):
                    crew_id_elem = record.find(f"Crew{i}Id")
                    crew_name_elem = record.find(f"Crew{i}Name")

                    if crew_id_elem is not None and crew_id_elem.text:
                        person_id = self.resolve_or_create_entity(crew_id_elem.text, "person")
                        crew.append(person_id)
                    elif crew_name_elem is not None and crew_name_elem.text:
                        person_id = self.resolve_or_create_entity(crew_name_elem.text, "person")
                        crew.append(person_id)

                # Cox - can also be referenced by ID or name
                cox_id_elem = record.find("CoxId")
                cox_name_elem = record.find("CoxName")

                if cox_id_elem is not None and cox_id_elem.text:
                    cox_id = self.resolve_or_create_entity(cox_id_elem.text, "person")
                    crew.insert(0, cox_id)  # Cox goes first
                elif cox_name_elem is not None and cox_name_elem.text:
                    cox_id = self.resolve_or_create_entity(cox_name_elem.text, "person")
                    crew.insert(0, cox_id)  # Cox goes first

                entry["crew"] = crew

                # Destination
                dest_id_elem = record.find("DestinationId")
                dest_name_elem = record.find("DestinationName")

                if dest_id_elem is not None and dest_id_elem.text:
                    entry["dest"] = self.resolve_or_create_entity(dest_id_elem.text, "destination")
                elif dest_name_elem is not None and dest_name_elem.text:
                    entry["dest"] = self.resolve_or_create_entity(dest_name_elem.text, "destination")

                # Distance
                distance_elem = record.find("Distance")
                if distance_elem is not None:
                    distance = self.parse_distance(distance_elem.text)
                    if distance > 100:
                        self.stats["excessive_distances"] += 1
                        logger.warning(f"Found entry with distance {distance}km, skipping")
                        logger.debug(f"Full XML record: {ET.tostring(record, encoding='utf-8').decode('utf-8')}")
                        continue
                    entry["dist"] = distance

                # Session type
                session_type = record.find("SessionType")
                if session_type is not None:
                    entry["type"] = session_type.text.lower()

                # Comments
                comments = record.find("Comments")
                if comments is not None:
                    entry["note"] = comments.text

                self.logbooks.append(entry)

    def export_json(self, output_dir: str):
        """Export all data to JSON files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Convert to lists for JSON export
        exports = {
            "boats.json": list(self.boats.values()),
            "persons.json": list(self.persons.values()),
            "destinations.json": list(self.destinations.values()),
            "logbooks.json": self.logbooks
        }

        for filename, data in exports.items():
            gz_filename = filename + ".gz"
            with gzip.open(output_path / gz_filename, 'wt', encoding='utf-8') as f:
                f.write(json.dumps(data, separators=(',', ':')))
        logger.info(f"Export completed")
        logger.info(f"Stats: {self.stats}")
        logger.info(f"  Exported boats: {len(self.boats)}")
        logger.info(f"  Exported persons: {len(self.persons)}")
        logger.info(f"  Exported destinations: {len(self.destinations)}")
        logger.info(f"  Exported logbook entries: {len(self.logbooks)}")
        logger.info(f"  Skipped logbook entries due to excessive distance: {self.stats['excessive_distances']}")
        logger.info(f"  Skipped logbook entries due to future year: {self.stats['future_years']}")
        errs = self.stats['excessive_distances'] + self.stats['future_years']
        logger.info(f"Percentage errors: {errs / (errs + len(self.logbooks)) * 100:.2f}%")

    def check_consistency(self) -> List[str]:
        """Check consistency of the imported data and return list of errors"""
        errors = []

        # Check that all IDs in logbooks can be found in respective entity dicts
        for i, entry in enumerate(self.logbooks):
            if "boat" not in entry:
                errors.append(f"Logbook entry {i}: no boat ID")
            elif entry["boat"] not in self.boats:
                errors.append(f"Logbook entry {i}: boat ID '{entry['boat']}' not found in boats")

            if "crew" not in entry:
                errors.append(f"Logbook entry {i}: no crew IDs")
            else:
                for j, person_id in enumerate(entry["crew"]):
                    if person_id not in self.persons:
                        errors.append(f"Logbook entry {i}: crew[{j}] ID '{person_id}' not found in persons")

            # Check destination ID
            if "dest" in entry and entry["dest"] not in self.destinations:
                errors.append(f"Logbook entry {i}: destination ID '{entry['dest']}' not found in destinations")

        # Check that boats with same name have consistent ID patterns (same oid)
        boats_by_name = {}
        for boat_id, boat in self.boats.items():
            name = boat["name"]
            if name not in boats_by_name:
                boats_by_name[name] = []
            boats_by_name[name].append((boat_id, boat["oid"]))
        for name, boat_list in boats_by_name.items():
            if len(boat_list) == 1:
                continue
            if len(set(boat["oid"] for boat in boat_list)) > 1:
                errors.append(f"Boats with name '{name}' have different original IDs: {oids}")
            if len(set(boat["id"][:-2] for boat in boat_list)) > 1:
                errors.append(f"Boats with name '{name}' have different IDs: {ids}")

        # Check that every person has at least first or last name
        for person_id, person in self.persons.items():
            has_first = "fn" in person and person["fn"] is not None and person["fn"].strip()
            has_last = "ln" in person and person["ln"] is not None and person["ln"].strip()
            if not has_first and not has_last:
                errors.append(f"Person '{person_id}' has neither first name nor last name")

        return errors

def main():
    parser = argparse.ArgumentParser(description="Convert EFA backup files to JSON")
    parser.add_argument("--boats", required=True, help="Boats file (boats.efa2boats)")
    parser.add_argument("--persons", required=True, help="Persons file (persons.efa2persons)")
    parser.add_argument("--destinations", required=True, help="Destinations file (destinations.efa2destinations)")
    parser.add_argument("--logbooks", required=True, nargs="+", help="Logbook files (supports globs like *.efa2logbook)")
    parser.add_argument("--output", "-o", default="output", help="Output directory (default: output)")
    parser.add_argument("--verbose", "-v", action="count", default=0, help="Increase verbosity")

    args = parser.parse_args()

    # Set up logging
    log_level = logging.INFO
    if args.verbose == 1:
        log_level = logging.DEBUG
    elif args.verbose > 1:
        log_level = logging.TRACE
    logging.basicConfig(level=log_level)

    # Expand globs for logbooks
    logbook_files = []
    for pattern in args.logbooks:
        matches = glob.glob(pattern)
        if matches:
            logbook_files.extend(matches)
        else:
            # If no glob matches, try as literal filename
            if Path(pattern).exists():
                logbook_files.append(pattern)
            else:
                logger.warning(f"No files found matching pattern: {pattern}")

    if not logbook_files:
        logger.error("No logbook files found")
        return 1

    importer = EFAImporter()

    logger.info("Processing boats...")
    importer.process_boats(args.boats)

    logger.info("Processing persons...")
    importer.process_persons(args.persons)

    logger.info("Processing destinations...")
    importer.process_destinations(args.destinations)

    logger.info(f"Processing {len(logbook_files)} logbook files...")
    importer.process_logbooks(logbook_files)

    logger.info(f"Exporting to {args.output}/...")
    importer.export_json(args.output)

    logger.info("Checking consistency...")
    errors = importer.check_consistency()
    if errors:
        logger.error(f"Found {len(errors)} consistency errors:")
        for error in errors:
            logger.error(f"  - {error}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())