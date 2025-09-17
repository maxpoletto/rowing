# Data model

Data types are:
* Athlete
* Group
* Hull
* Boat
* Boathouse
* Outing
* Destination
* Damage

Athlete comprises:
* ID: integer
* EFA ID: string
* First name: string
* Last name: string
* Gender: enum (male / female / other)
* Year of birth: integer
* IsRepeatable: boolean (can appear multiple times in one crew, e.g., “Guest” or “Student”)

Group comprises:
* ID: integer
* EFA ID: string
* Description: string
* Color: string

Athletes are matched to groups by a link table with the following fields:
* Athlete ID
* Group ID

For now an athlete may belong to exactly one group.

Hull comprises:
* ID: integer
* EFA ID: string (may be the same as a boat EFA ID)
* Name: string
* Type: enum (Race / Gig / Coastal / other)
* Crew size: integer
* Coxed: boolean
* Boathouse ID

Hulls are matched to groups by a link table with the following fields:
* Hull ID
* Group ID

For now a boat may belong to exactly one group.

Boat comprises:
* ID: integer
* EFA ID: string (may be the same as a hull EFA ID, or hull EFA ID + “-vN” where N is 1 or 2 and denotes a variant based on rigging)
* Hull ID: integer
* Rigging: enum (sweep / scull)

Boathouse comprises:
* ID: integer
* Name: string
* Address: string

Destination comprises:
* ID: integer
* EFA ID: string
* Name: string
* Km: integer
* Note: string

Outing comprises:
* ID: integer
* EFA ID: string
* Date: date
* Start time: time
* End time: time
* Cox ID: integer
* Crew1 ID … Crew8 ID: integer
* Cox Name: string
* Crew1 Name … Crew8 Name: string
* Destination ID: integer
* Km: integer
* Note: string

Cox and Crew Names are non-null iff the corresponding IDs denote a repeatable athlete.
Km defaults to the destination’s value, but is stored separately because it may be altered.

Damage comprises:
* ID: integer
* Severity: integer
* Resolved: boolean
* Description: string
* Hull ID: integer
* Boat ID: integer

Exactly one of Hull or Boat ID may be set. If Hull ID is non-null, affects all boats with that hull.


# Options

* Is it possible to create an outing with an undefined destination?


