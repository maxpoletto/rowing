Elbar (Electronic Log Book App for Rowing) is open-source, MIT-licensed software for keeping track of boats and activity in a rowing club.


It is designed to be compatible with EFA, the de-facto standard boathouse log software in German-speaking countries, but also natively supports online access and is built with modern technologies.


# Architecture overview


An Elbar installation consists of one or more communicating instances. If more than one instance exists, one of the instances must have a public IP and is designated *primary*. Other *secondary* instances need not have public IPs but establish secure bidirectional channels with the master for communication. State is shared across all instances via replay of immutable timestamped event logs.


Typically, one or more secondary instances are deployed locally at a club’s boathouse(s) (with internet access but no stable public IP), while the primary instance is deployed on a cloud server.


This architecture provides online access (e.g., to users from home) while allowing boathouse instances to operate in the absence of a network connection.


Each instance consists of a backend implemented in Django and backed by SQLite, and a frontend implemented in pure JavaScript. The code is deployed as a Docker image that mounts a local directory for (mutable) database storage. Updates happen by installing a new Docker image. An explicit design goal of Elbar is to minimize dependencies and reduce the frequency of software updates.


# Configuration


Initial installation happens by running a script to install a Docker image and pointing it to the directory for database storage. Subsequent software updates occur via the same script.


After software installation, all subsequent configuration happens via the web UI.


## Data


Elbar accepts EFA backup files as input and can generate EFA backup files as output. This ensures data portability for users between EFA and Elbar: there is no data lock-in.


When an EFA backup file is ready as input, Elbar attempts to *merge* its contents into its existing database state and reports any conflicts. Of course, starting from a blank Elbar state, or resetting the state prior to import, exactly replicates the EFA state in the backup.


Elbar also accepts information about athletes, boats, destinations, and outings in CSV format. More on the specific format below.


## Instances


An instance can be denoted as primary or secondary.


If the instance is made primary, the UI generates a token (that the user can choose to regenerate).


If the instance is made secondary, the user must configure it with the hostname or IP address of the primary and the token issued by the primary.


All secondary instances in the system must share the same primary.


## Appearance


Users can upload a club logo and some introductory text.


They can also choose from a small number of color palettes.


## Options


# Access model
