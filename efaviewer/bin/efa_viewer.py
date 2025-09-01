#!/usr/bin/env python3
"""
EFA XML Viewer/Editor Tool

A command-line tool to view and edit EFA XML files with pretty printing,
ID-to-name resolution, and basic editing capabilities.
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any


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
    parser.add_argument("--logbook", required=True, help="Logbook file to view")
    parser.add_argument("--limit", "-n", type=int, help="Limit number of entries to display")
    
    args = parser.parse_args()
    
    viewer = EfaViewer()
    
    print("Loading reference data...")
    viewer.load_boats(args.boats)
    viewer.load_persons(args.persons)
    
    if args.destinations:
        viewer.load_destinations(args.destinations)
    
    print(f"Loaded {len(viewer.boats)} boats, {len(viewer.persons)} persons")
    if viewer.destinations:
        print(f"Loaded {len(viewer.destinations)} destinations")
    
    viewer.pretty_print_logbook(args.logbook, args.limit)


if __name__ == "__main__":
    main()