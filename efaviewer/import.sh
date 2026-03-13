#!/bin/bash

D=/tmp/efa-import

rm -rf $D && \
mkdir $D && \
ssh efa@efa.belvoir-rc.ch ls /home/efa/backups | egrep efaBackup.\*zip | tail -1 | \
    xargs -I ff scp efa@efa.belvoir-rc.ch:/home/efa/backups/ff $D/latest.zip && \
unzip  $D/latest.zip -d $D && \
python3 bin/efa_importer.py --max-distance 500 \
    --boats $D/data/BelvoirRC/boats.efa2boats \
    --persons $D/data/BelvoirRC/persons.efa2persons \
    --destinations $D/data/BelvoirRC/destinations.efa2destinations \
    --logbooks $D/data/BelvoirRC/20\* \
    --output app/data/ &&
gunzip -kf app/data/*.gz
