#!/usr/bin/env python3
"""
EFA XML Viewer/Editor Tool

A command-line tool to view and edit EFA XML files with pretty printing,
ID-to-name resolution, and basic editing capabilities.
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
import re
from collections import defaultdict


class EfaViewer:
    def __init__(self):
        self.boats = {}
        self.persons = {}
        self.destinations = {}

    def load_boats(self, boats_file: str):
        """Load boats from efa2boats file"""
        tree = ET.parse(boats_file)
        root = tree.getroot()

        for record in root.findall(".//record"):
            boat_id = record.find("Id").text
            name = record.find("Name").text
            name_affix = record.find("NameAffix")

            # Handle boat variants
            last_variant = int(record.find("LastVariant").text)
            type_seats = record.find("TypeSeats").text.split(";")
            type_rigging = record.find("TypeRigging").text.split(";")
            type_coxing = record.find("TypeCoxing").text.split(";")

            # Skip boats with inconsistent variant counts
            if len(type_seats) != len(type_rigging) or len(type_seats) != len(type_coxing):
                continue

            n_variants = len(type_seats)

            for variant in range(1, n_variants + 1):
                variant_id = f"{boat_id}-v{variant}"

                boat_data = {
                    "id": variant_id,
                    "original_id": boat_id,
                    "name": name,
                    "variant": variant,
                    "seats": self._parse_seats(type_seats[variant - 1]),
                    "rigging": type_rigging[variant - 1].lower(),
                    "coxing": type_coxing[variant - 1].lower(),
                }

                if name_affix is not None:
                    boat_data["suffix"] = name_affix.text

                self.boats[variant_id] = boat_data
                # Also store by original ID for lookup
                self.boats[boat_id] = boat_data

    def load_persons(self, persons_file: str):
        """Load persons from efa2persons file"""
        tree = ET.parse(persons_file)
        root = tree.getroot()

        for record in root.findall(".//record"):
            person_id = record.find("Id").text
            first_name_elem = record.find("FirstName")
            last_name_elem = record.find("LastName")
            gender = record.find("Gender").text

            # Skip archived persons
            last_name = last_name_elem.text if last_name_elem is not None else None
            if last_name and last_name.startswith("archiveID:"):
                continue

            first_name = first_name_elem.text if first_name_elem is not None else None

            person_data = {
                "id": person_id,
                "first_name": first_name,
                "last_name": last_name,
                "gender": gender.lower(),
                "full_name": self._format_person_name(first_name, last_name)
            }

            self.persons[person_id] = person_data

    def load_destinations(self, destinations_file: str):
        """Load destinations from efa2destinations file"""
        tree = ET.parse(destinations_file)
        root = tree.getroot()

        for record in root.findall(".//record"):
            dest_id = record.find("Id").text
            name = record.find("Name").text

            dest_data = {
                "id": dest_id,
                "name": name,
            }

            distance_elem = record.find("Distance")
            if distance_elem is not None:
                dest_data["distance"] = self._parse_distance(distance_elem.text)

            self.destinations[dest_id] = dest_data

    def _parse_seats(self, seats_str: str) -> int:
        """Parse seats string like '4X', '8', '2' and return integer"""
        if not seats_str or seats_str == "unknown":
            return 0

        import re
        match = re.search(r'(\d+)', seats_str)
        if match:
            return int(match.group(1))
        return 0

    def _parse_distance(self, distance_str: str) -> Optional[int]:
        """Parse distance string and return rounded km as integer"""
        if not distance_str:
            return None

        import re
        match = re.search(r'(\d+(?:\.\d+)?)', distance_str)
        if match:
            return round(float(match.group(1)))
        return None

    def _format_person_name(self, first_name: str, last_name: str) -> str:
        """Format person name for display"""
        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif last_name:
            return last_name
        elif first_name:
            return first_name
        return "Unknown"

    def _resolve_boat_name(self, boat_id: str, variant: int = None) -> str:
        """Resolve boat ID to name"""
        if variant:
            variant_id = f"{boat_id}-v{variant}"
            if variant_id in self.boats:
                boat = self.boats[variant_id]
                suffix = f" ({boat['suffix']})" if 'suffix' in boat else ""
                rigging = f" - {boat['rigging'].title()}" if boat['rigging'] != 'unknown' else ""
                return f"{boat['name']}{suffix}{rigging}"

        if boat_id in self.boats:
            boat = self.boats[boat_id]
            suffix = f" ({boat['suffix']})" if 'suffix' in boat else ""
            rigging = f" - {boat['rigging'].title()}" if boat['rigging'] != 'unknown' else ""
            return f"{boat['name']}{suffix}{rigging}"

        return f"Unknown Boat ({boat_id})"

    def _resolve_person_name(self, person_id: str) -> str:
        """Resolve person ID to name"""
        if person_id in self.persons:
            return self.persons[person_id]["full_name"]
        return f"Unknown Person ({person_id})"

    def _resolve_destination_name(self, dest_id: str) -> str:
        """Resolve destination ID to name"""
        if dest_id in self.destinations:
            dest = self.destinations[dest_id]
            distance_info = f" ({dest['distance']}km)" if 'distance' in dest else ""
            return f"{dest['name']}{distance_info}"
        return f"Unknown Destination ({dest_id})"

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison (lowercase, remove accents, extra spaces)"""
        # Simple normalization - can be enhanced with unicode normalization
        import unicodedata
        normalized = unicodedata.normalize('NFD', name.lower().strip())
        # Remove combining characters (accents)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        return normalized

    def _find_similar_names_generic(self, name_items: List[Tuple[str, str]], threshold: int = 2) -> Dict[str, List[Tuple[str, str, int]]]:
        """Generic method to find clusters of similar names"""
        clusters = defaultdict(list)
        processed = set()

        for i, (id1, name1) in enumerate(name_items):
            if id1 in processed:
                continue

            cluster = [(id1, name1, 0)]  # (id, name, distance)
            processed.add(id1)

            norm_name1 = self._normalize_name(name1)

            for j, (id2, name2) in enumerate(name_items):
                if i != j and id2 not in processed:
                    norm_name2 = self._normalize_name(name2)
                    distance = self._levenshtein_distance(norm_name1, norm_name2)

                    if distance <= threshold:
                        cluster.append((id2, name2, distance))
                        processed.add(id2)

            if len(cluster) > 1:  # Only keep clusters with multiple names
                clusters[f"cluster_{len(clusters)}"] = cluster

        return dict(clusters)

    def _find_names_by_pattern_generic(self, name_items: List[Tuple[str, str]], pattern: str) -> List[Tuple[str, str]]:
        """Generic method to find names matching a regex pattern"""
        regex = re.compile(pattern, re.IGNORECASE)
        matches = []

        for identifier, name in name_items:
            if regex.search(name):
                matches.append((identifier, name))

        return matches

    def find_similar_names(self, threshold: int = 2) -> Dict[str, List[Tuple[str, str, int]]]:
        """Find clusters of similar person names within edit distance threshold"""
        names = [(person_id, person["full_name"]) for person_id, person in self.persons.items()]
        return self._find_similar_names_generic(names, threshold)

    def find_names_by_pattern(self, pattern: str) -> List[Tuple[str, str]]:
        """Find person names matching a regex pattern"""
        names = [(person_id, person["full_name"]) for person_id, person in self.persons.items()]
        return self._find_names_by_pattern_generic(names, pattern)

    def extract_names_from_logbook(self, logbook_file: str) -> List[Tuple[str, str]]:
        """Extract all names from logbook entries, returning (name, source_info) tuples"""
        tree = ET.parse(logbook_file)
        root = tree.getroot()

        names = []  # (name, source_info)
        seen = set()  # To avoid duplicates

        for record in root.findall(".//record"):
            entry_id = record.find("EntryId").text
            date = record.find("Date").text

            # Check crew names
            for i in range(1, 20):
                crew_name_elem = record.find(f"Crew{i}Name")
                if crew_name_elem is not None and crew_name_elem.text:
                    name = crew_name_elem.text.strip()
                    if name not in seen:
                        names.append((name, f"Entry {entry_id} ({date}) - Crew{i}Name"))
                        seen.add(name)

            # Check cox name
            cox_name_elem = record.find("CoxName")
            if cox_name_elem is not None and cox_name_elem.text:
                name = cox_name_elem.text.strip()
                if name not in seen:
                    names.append((name, f"Entry {entry_id} ({date}) - CoxName"))
                    seen.add(name)

        return names

    def find_similar_logbook_names(self, logbook_file: str, threshold: int = 2) -> Dict[str, List[Tuple[str, str, int]]]:
        """Find clusters of similar names from logbook entries"""
        names = self.extract_names_from_logbook(logbook_file)
        return self._find_similar_names_generic(names, threshold)

    def find_logbook_names_by_pattern(self, logbook_file: str, pattern: str) -> List[Tuple[str, str]]:
        """Find logbook names matching a regex pattern"""
        names = self.extract_names_from_logbook(logbook_file)
        return self._find_names_by_pattern_generic(names, pattern)

    def print_name_analysis(self, similarity_threshold: int = 2, pattern: str = None, logbook_file: str = None):
        """Print analysis of similar names and pattern matches from persons file and optionally logbook"""
        print("\n=== Name Analysis ===\n")

        # Analyze persons file
        print("=== PERSONS FILE ANALYSIS ===")
        if pattern:
            print(f"Names matching pattern '{pattern}':")
            print("-" * 40)
            matches = self.find_names_by_pattern(pattern)
            for person_id, name in sorted(matches, key=lambda x: x[1]):
                print(f"  {name} ({person_id[:8]}...)")
            print(f"\nTotal matches: {len(matches)}\n")

        print(f"Similar name clusters (edit distance ≤ {similarity_threshold}):")
        print("-" * 50)
        clusters = self.find_similar_names(similarity_threshold)

        if not clusters:
            print("No similar name clusters found.\n")
        else:
            for cluster_name, cluster in clusters.items():
                print(f"{cluster_name.replace('_', ' ').title()}:")
                for person_id, name, distance in sorted(cluster, key=lambda x: x[2]):
                    distance_info = f" (distance: {distance})" if distance > 0 else ""
                    print(f"  • {name} ({person_id[:8]}...){distance_info}")
                print()

            print(f"Total clusters: {len(clusters)}")
            total_similar = sum(len(cluster) for cluster in clusters.values())
            print(f"Total names in clusters: {total_similar}")

        # Analyze logbook if provided
        if logbook_file:
            print(f"\n=== LOGBOOK ANALYSIS ({Path(logbook_file).name}) ===")

            if pattern:
                print(f"Names matching pattern '{pattern}':")
                print("-" * 40)
                matches = self.find_logbook_names_by_pattern(logbook_file, pattern)
                for name, source in sorted(matches, key=lambda x: x[0]):
                    print(f"  {name}")
                    print(f"    First seen: {source}")
                print(f"\nTotal matches: {len(matches)}\n")

            print(f"Similar name clusters (edit distance ≤ {similarity_threshold}):")
            print("-" * 50)
            clusters = self.find_similar_logbook_names(logbook_file, similarity_threshold)

            if not clusters:
                print("No similar name clusters found.\n")
            else:
                for cluster_name, cluster in clusters.items():
                    print(f"{cluster_name.replace('_', ' ').title()}:")
                    for name, source, distance in sorted(cluster, key=lambda x: x[2]):
                        distance_info = f" (distance: {distance})" if distance > 0 else ""
                        print(f"  • {name}{distance_info}")
                        print(f"    First seen: {source}")
                    print()

                print(f"Total clusters: {len(clusters)}")
                total_similar = sum(len(cluster) for cluster in clusters.values())
                print(f"Total names in clusters: {total_similar}")

    def pretty_print_logbook(self, logbook_file: str, limit: int = None):
        """Pretty print logbook entries with ID resolution"""
        tree = ET.parse(logbook_file)
        root = tree.getroot()

        print(f"\n=== Logbook: {Path(logbook_file).name} ===\n")

        entries = root.findall(".//record")
        if limit:
            entries = entries[:limit]

        for i, record in enumerate(entries):
            entry_id = record.find("EntryId").text
            date = record.find("Date").text

            print(f"Entry {entry_id} - {date}")
            print("-" * 40)

            # Boat information
            boat_id_elem = record.find("BoatId")
            boat_variant_elem = record.find("BoatVariant")

            if boat_id_elem is not None:
                boat_id = boat_id_elem.text
                variant = int(boat_variant_elem.text) if boat_variant_elem is not None else 1
                boat_name = self._resolve_boat_name(boat_id, variant)
                print(f"  Boat: {boat_name}")

            # Crew information
            crew = []

            # Check for cox
            cox_id_elem = record.find("CoxId")
            if cox_id_elem is not None:
                cox_name = self._resolve_person_name(cox_id_elem.text)
                crew.append(f"Cox: {cox_name}")

            # Check for crew members
            for j in range(1, 20):
                crew_elem = record.find(f"Crew{j}Id")
                if crew_elem is not None:
                    crew_name = self._resolve_person_name(crew_elem.text)
                    crew.append(f"Crew{j}: {crew_name}")

            if crew:
                print(f"  Crew: {', '.join(crew)}")

            # Times
            start_time_elem = record.find("StartTime")
            end_time_elem = record.find("EndTime")
            if start_time_elem is not None and end_time_elem is not None:
                start_time = start_time_elem.text.split(":", 2)[:2]
                end_time = end_time_elem.text.split(":", 2)[:2]
                print(f"  Time: {':'.join(start_time)} - {':'.join(end_time)}")

            # Destination and distance
            dest_id_elem = record.find("DestinationId")
            if dest_id_elem is not None:
                dest_name = self._resolve_destination_name(dest_id_elem.text)
                print(f"  Destination: {dest_name}")

            distance_elem = record.find("Distance")
            if distance_elem is not None:
                print(f"  Distance: {distance_elem.text}")

            # Session type
            session_type_elem = record.find("SessionType")
            if session_type_elem is not None:
                print(f"  Type: {session_type_elem.text}")

            # Comments
            comments_elem = record.find("Comments")
            if comments_elem is not None:
                print(f"  Comments: {comments_elem.text}")

            print()

            if limit and i >= limit - 1:
                break

        total_entries = len(root.findall(".//record"))
        if limit and total_entries > limit:
            print(f"... ({total_entries - limit} more entries)")


def main():
    parser = argparse.ArgumentParser(description="View and edit EFA XML files")
    parser.add_argument("--boats", required=True, help="Boats file (boats.efa2boats)")
    parser.add_argument("--persons", required=True, help="Persons file (persons.efa2persons)")
    parser.add_argument("--destinations", help="Destinations file (destinations.efa2destinations)")

    parser.add_argument("--logbook", help="Logbook file(s) to process (supports globs like '*.efa2logbook')")
    parser.add_argument("--analyze-names", action="store_true", help="Analyze person names for duplicates and patterns")

    # Options for logbook viewing
    parser.add_argument("--limit", "-n", type=int, help="Limit number of entries to display")

    # Options for name analysis
    parser.add_argument("--similarity-threshold", type=int, default=2, help="Edit distance threshold for similar names (default: 2)")
    parser.add_argument("--pattern", help="Regex pattern to match person names")

    args = parser.parse_args()

    # Require at least one action
    if not args.logbook and not args.analyze_names:
        parser.error("Must specify either --logbook (to view) or --analyze-names (to analyze names), or both")

    viewer = EfaViewer()

    print("Loading reference data...")
    viewer.load_boats(args.boats)
    viewer.load_persons(args.persons)

    if args.destinations:
        viewer.load_destinations(args.destinations)

    print(f"Loaded {len(viewer.boats)} boats, {len(viewer.persons)} persons")
    if viewer.destinations:
        print(f"Loaded {len(viewer.destinations)} destinations")

    if args.analyze_names:
        # If logbook is also specified, include it in the analysis
        viewer.print_name_analysis(args.similarity_threshold, args.pattern, args.logbook)
    elif args.logbook:
        viewer.pretty_print_logbook(args.logbook, args.limit)


if __name__ == "__main__":
    main()