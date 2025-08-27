#!/bin/bash

D=/tmp/efa-import

rm -rf $D && \
mkdir $D && \
ssh efa@efa.belvoir-rc.ch ls /home/efa/backups | egrep efaBackup.\*zip | tail -1 | \
    xargs -I ff scp efa@efa.belvoir-rc.ch:/home/efa/backups/ff $D/latest.zip && \
unzip  $D/latest.zip -d $D && \
python3 bin/efa_importer.py \
    --boats $D/data/BRC/boats.efa2boats \
    --persons $D/data/BRC/persons.efa2persons \
    --destinations $D/data/BRC/destinations.efa2destinations \
    --logbooks $D/data/BRC/20\* \
    --output app/data/ &&
gunzip -kf app/data/*.gz
